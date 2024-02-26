import contextlib
import sys
import time
from argparse import ArgumentParser
from concurrent.futures import Future, ThreadPoolExecutor
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
    default=0.25,
    help=dedent(
        """
            How long to wait between firing requests.
        """,
    ).strip(),
)
args = parser.parse_args()

WORKERS = min(round(1 / args.seconds_per_request), 8)


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

        console.log(`${url}?${queryParams}`);

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


died = False


def make_pair_exp_backoff(
    driver: chrome.webdriver.Chrome,
    pair: PendingPair,
) -> Pair:
    backoff = 1
    while not died:
        try:
            return make_pair(driver, pair)
        except Exception as e:
            if died:
                raise

            print(f"Failed: {e}\n\nTrying again in {backoff} second(s)")
            time.sleep(backoff)
            backoff *= 2
    raise TimeoutError


with (
    ThreadPoolExecutor(max_workers=WORKERS) as executor,
    contextlib.ExitStack() as stack,
):
    drivers = list(
        executor.map(
            lambda _i: stack.enter_context(chrome.driver()),
            range(WORKERS),
        ),
    )
    list(executor.map(lambda d: d.get("https://neal.fun/infinite-craft"), drivers))

    pending_pair_generator = persistence.select_pending_pairs()
    futures: dict[PendingPair, Future[Pair]] = {}

    while True:
        try:
            # clear out completed futures
            for pending_pair, future in list(futures.items()):
                if not future.done():
                    continue

                if pending_pair_generator is not None:
                    del pending_pair_generator
                    pending_pair_generator = None

                pair = future.result()
                print(pair)
                persistence.record_pair(pair)
                del futures[pending_pair]

            if pending_pair_generator is None:
                pending_pair_generator = persistence.select_pending_pairs()

            if len(futures) <= WORKERS:
                for pending_pair in pending_pair_generator:
                    if pending_pair in futures:
                        continue

                    if not args.allow_numbers and pending_pair.numeric:
                        continue

                    driver = drivers.pop(0)
                    drivers.append(driver)
                    futures[pending_pair] = executor.submit(
                        make_pair_exp_backoff,
                        driver,
                        pending_pair,
                    )

                    break
                else:
                    if not futures:
                        print(
                            "All possible pairs explored! There are no other possible pairings!",
                        )
                        sys.exit()

            time.sleep(args.seconds_per_request)
        except:
            died = True
            executor.shutdown(wait=False, cancel_futures=True)
            raise
