import itertools
import random
import time
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Generator

import chrome
import persistence
from pair import Pair

directory = Path(__file__).parent

parser = ArgumentParser()
parser.add_argument(
    "strategy",
    type=str,
    choices=["random", "breadth", "depth"],
    default="depth",
    nargs="?",
    help=dedent(
        """
            In what order should pairs be tested?
                random: Simply select pairs at random.
                breadth: Go from top to bottom, alphabetically, until all possible combinations have been exhausted. Then, restart and use the newly-created elements. (use old elements first)
                depth: Same as breadth, but the instant that a new element is created, immediately try using it to make other elements. (use new elements first)
        """,
    ).strip(),
)
parser.add_argument(
    "--temperature",
    type=float,
    default=0.25,
    help=dedent(
        """
            The chance (from 0 to 1) per-pair to randomly select a strategy instead of using the provided one.
        """,
    ).strip(),
)
args = parser.parse_args()

known_elements, known_pairs = persistence.load_all()

for add in {"Water", "Fire", "Wind", "Earth"} - known_elements:
    known_elements.add(add)
    persistence.record_known_element(add)


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


def complete_pair(
    driver: chrome.webdriver.Chrome,
    pair: Pair,
) -> bool:
    response = execute_request(
        driver,
        "https://neal.fun/api/infinite-craft/pair",
        {"first": pair.inputs[0], "second": pair.inputs[1]},
    )

    if "result" not in response:
        msg = f"Invalid response: {response!r}"
        raise ValueError(msg)

    pair.output = response["result"]
    return response["isNew"]


def complete_pair_exp_backoff(
    driver: chrome.webdriver.Chrome,
    pair: Pair,
) -> bool:
    backoff = 1
    while True:
        try:
            return complete_pair(driver, pair)
        except Exception as e:
            print(f"Failed: {e}\n\nTrying again in {backoff} second(s)")
            time.sleep(backoff / 2)
            driver.refresh()
            time.sleep(backoff / 2)
            backoff *= 2


recently_found: list[str] = []


def strategy_random(
    driver: chrome.webdriver.Chrome,
) -> Generator[tuple[Pair, bool], None, None]:
    while True:
        elements = tuple(known_elements)
        pair = Pair(*random.choices(elements, k=2))

        if pair in known_pairs:
            continue

        yield pair, complete_pair_exp_backoff(driver, pair)


def strategy_breadth(
    driver: chrome.webdriver.Chrome,
) -> Generator[tuple[Pair, bool], None, None]:
    while True:
        _known_elements = tuple(sorted(known_elements))
        for a in _known_elements:
            for b in _known_elements:
                pair = Pair(a, b)

                if pair in known_pairs:
                    continue

                yield pair, complete_pair_exp_backoff(driver, pair)


def strategy_depth(
    driver: chrome.webdriver.Chrome,
) -> Generator[tuple[Pair, bool], None, None]:
    while True:
        found = False
        for a in reversed(recently_found):
            for b in itertools.chain(reversed(recently_found), known_elements):
                if found:
                    break

                pair = Pair(a, b)
                if pair in known_pairs:
                    continue

                new = complete_pair_exp_backoff(driver, pair)
                assert pair.output is not None

                found = True
                break

            if found:
                yield pair, new
                break

        if not found:
            yield next(strategy_random(driver))


strategies = {
    "random": strategy_random,
    "depth": strategy_depth,
    "breadth": strategy_breadth,
}

with chrome.driver() as driver:
    driver.get("https://neal.fun/infinite-craft")

    strategy_iterators = {
        name: iter(strategy(driver)) for name, strategy in strategies.items()
    }

    while True:
        if random.random() < args.temperature:
            strategy_iterator = random.choice(tuple(strategy_iterators.values()))
        else:
            strategy_iterator = strategy_iterators[args.strategy]

        while True:
            pair, new = next(strategy_iterator)
            if pair not in known_pairs:
                break

        assert pair.output is not None

        new_to_me = pair.output not in known_elements
        if new_to_me:
            recently_found.append(pair.output)

        known_pairs.add(pair)
        persistence.record_pair(pair)

        known_elements.add(pair.output)
        persistence.record_known_element(pair.output)

        if new:
            addendum = " (New Discovery!)"
        elif new_to_me:
            addendum = " (New to Me!)"
        else:
            addendum = ""

        print(f"{pair}{addendum}", end=" " * 20 + "\n")
        print(
            f"Explored {len(known_pairs):,d} / {len(known_elements) ** 2:,d} = {len(known_pairs) / len(known_elements)**2:.3%}",
            end="\r",
        )

        if new:
            with (directory / "discovered.txt").open("a") as f:
                print(f"{datetime.now(timezone.utc).isoformat()} {pair}", file=f)

        time.sleep(0.25)
