import sys
import time
from argparse import ArgumentParser
from base64 import b64encode
from pathlib import Path
from textwrap import dedent

import api
import cloudflare
import persistence

directory = Path(__file__).parent

parser = ArgumentParser()
parser.add_argument(
    "command",
    type=str,
    choices=["scan", "dump"],
    default="scan",
    nargs="?",
    help=dedent(
        """
            The program which should be run:
                scan: Create database schemas, if they don't already exist.
                backfill: Fetch all calls from CallRail and fill the database.
        """,
    ).strip(),
)
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


def scan(allow_numbers: bool, seconds_per_request: float) -> None:
    headers = cloudflare.get_headers()
    timed_out = set()

    last_status_line_length = 0
    last_sleep_ended_at = 0
    while True:
        for pending_pair in persistence.select_pending_pairs():
            if not allow_numbers and pending_pair.numeric:
                continue
            if pending_pair in timed_out:
                continue
            break
        else:
            print("All possible pairs explored! There are no other possible pairings!")
            sys.exit()

        try:
            pair = api.make_pair_exp_backoff(pending_pair, headers, timeout=5)
        except TimeoutError:
            print(f"Timed out while trying to make pair, moving on: {pending_pair}")
            timed_out.add(pending_pair)
            continue

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
        sleep_remaining = seconds_per_request - already_slept
        if sleep_remaining > 0:
            time.sleep(seconds_per_request - already_slept)
        last_sleep_ended_at = time.perf_counter()


def dump() -> None:
    def b64(x: str) -> str:
        return b64encode(x.encode()).decode()

    lines = []
    last_print_at = time.perf_counter()
    n, _ = persistence.counts()
    for i, (element, discovered) in enumerate(
        persistence.select_elements_and_discovered(),
    ):
        lines.append(f"{b64(element.emoji)},{b64(element.name)},{discovered:d}")

        now = time.perf_counter()
        if now - last_print_at > 1:
            print(f"Loaded: {i + 1}/{n}", end="\r")
            last_print_at = now

    data = " ".join(lines)

    print(
        dedent(
            f"""
            let data = "{data}";
            let storage = JSON.parse(localStorage.getItem("infinite-craft-data")) || {{}};
            storage.elements = storage.elements || [];

            const nameSet = new Set(storage.elements.map(element => element.text));

            function b64(x) {{
                return decodeURIComponent(escape(atob(x)));
            }}

            data.split(" ").forEach(line => {{
                let [emoji, name, discovered] = line.split(",");
                emoji = b64(emoji);
                name = b64(name);
                discovered = discovered === "1";

                if (!nameSet.has(name)) {{
                    storage.elements.push({{ text: name, emoji: emoji, discovered: discovered }});
                }}
            }});

            localStorage.setItem("infinite-craft-data", JSON.stringify(storage));
            """,
        ).strip(),
    )


if __name__ == "__main__":
    args = parser.parse_args()
    if args.command == "scan":
        scan(args.allow_numbers, args.seconds_per_request)
    elif args.command == "dump":
        dump()
