import sys
import time
from argparse import ArgumentParser
from pathlib import Path
from textwrap import dedent

import chrome
import persistence
from models import Element, Pair, PendingPair

directory = Path(__file__).parent

parser = ArgumentParser()
parser.add_argument(
    "--allow-numbers",
    action="store_true",
    help=dedent(
        """
            If not specified, the program will not bother pairing two elements which are both more than 50% numeric.
            This useful since those pairings _usually_ just result in a bigger number, which is entirely uninteresting
            (regardless of the fact that it's almost always a New Discovery).
        """,
    ).strip(),
)
parser.add_argument(
    "--seconds-per-request",
    type=float,
    default=0.5,
    help=dedent(
        """
            How long to wait between firing requests.
        """,
    ).strip(),
)
args = parser.parse_args()


def execute_request(
    driver: chrome.webdriver.Chrome,
    url: str,
    params: dict[str, str],
) -> dict:
    js_code = """
        var callback = arguments[arguments.length - 1];
        var url = arguments[0];
        var params = arguments[1];

        var queryParams = new URLSearchParams(params).toString();

        fetch(`${url}?${queryParams}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok, status: ' + response.status);
                }
                return response.json();
            })
            .then(data => callback({'data': data}))
            .catch(error => callback({'error': error.message}));
    """
    result = driver.execute_async_script(js_code, url, params)

    if "error" in result:
        raise ValueError(result["error"])

    return result["data"]


def make_pair(
    driver: chrome.webdriver.Chrome,
    pair: PendingPair,
) -> Pair:
    response = execute_request(
        driver,
        "https://neal.fun/api/infinite-craft/pair",
        {"first": pair.first.name, "second": pair.second.name},
    )

    if "result" not in response:
        msg = f"Invalid response: {response!r}"
        raise ValueError(msg)

    return Pair(
        pair.first,
        pair.second,
        Element(response["result"], response.get("emoji")),
        response.get("isNew"),
    )


def make_pair_exp_backoff(
    driver: chrome.webdriver.Chrome,
    pair: PendingPair,
) -> Pair:
    backoff = 1
    while True:
        try:
            return make_pair(driver, pair)
        except Exception as e:
            print(f"Failed: {e}\n\nTrying again in {backoff} second(s)")
            time.sleep(backoff / 2)
            driver.refresh()
            time.sleep(backoff / 2)
            backoff *= 2


with chrome.driver() as driver:
    driver.get("https://neal.fun/infinite-craft")
    last_sleep_ended_at = 0
    last_status_line_length = 0

    while True:
        for pending_pair in persistence.select_pending_pairs():
            if not args.allow_numbers and pending_pair.numeric:
                continue
            break
        else:
            print("All possible pairs explored! There are no other possible pairings!")
            sys.exit()

        pair = make_pair_exp_backoff(driver, pending_pair)
        persistence.record_pair(pair)
        element_count, pair_count = persistence.counts()
        possible_pair_count = (element_count**2 + element_count) // 2  # ncr(n, 2) + n

        pair_str = str(pair)
        print(
            pair_str,
            end=" " * max(last_status_line_length - len(pair_str), 0) + "        \n",
        )
        status_line = f"Explored {pair_count:,d} / {possible_pair_count:,d} = {pair_count / possible_pair_count:.3%} of pairs"
        last_status_line_length = len(status_line)
        print(status_line, end="\r")

        already_slept = time.perf_counter() - last_sleep_ended_at
        sleep_remaining = args.seconds_per_request - already_slept
        if sleep_remaining > 0:
            time.sleep(args.seconds_per_request - already_slept)
        last_sleep_ended_at = time.perf_counter()
