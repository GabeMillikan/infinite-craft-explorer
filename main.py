from argparse import ArgumentParser
from pathlib import Path
from textwrap import dedent

from dump import dump
from scan import scan

directory = Path(__file__).parent

parser = ArgumentParser()
parser.add_argument(
    "program",
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
    default=0.25,
    help=dedent(
        """
            How often requests should be sent.
        """,
    ).strip(),
)
parser.add_argument(
    "--threads",
    "-j",
    type=int,
    default=8,
    help=dedent(
        """
            Maximum concurrent requests.
            Note that `seconds-per-request` applies globally, not per-thread.
        """,
    ).strip(),
)


if __name__ == "__main__":
    args = parser.parse_args()
    if args.program == "scan":
        scan(args.allow_numbers, args.seconds_per_request, args.threads)
    elif args.program == "dump":
        dump()
