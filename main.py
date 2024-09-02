import sys
import time
from argparse import ArgumentParser
from pathlib import Path
from textwrap import dedent

import api
import cloudflare
import persistence

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


if __name__ == "__main__":
    headers = cloudflare.get_headers()
    timed_out = set()

    last_status_line_length = 0
    last_sleep_ended_at = 0
    while True:
        for pending_pair in persistence.select_pending_pairs():
            if not args.allow_numbers and pending_pair.numeric:
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
        sleep_remaining = args.seconds_per_request - already_slept
        if sleep_remaining > 0:
            time.sleep(args.seconds_per_request - already_slept)
        last_sleep_ended_at = time.perf_counter()
