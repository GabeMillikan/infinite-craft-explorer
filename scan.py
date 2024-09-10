import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Generator, TypeAlias

import api
import cloudflare
import persistence
from models import Pair, PendingPair

Failed: TypeAlias = set[PendingPair]
Futures: TypeAlias = dict[Future[Pair], PendingPair]
Headers: TypeAlias = dict[str, str]


def valid_pending_pairs(
    allow_numbers: bool,
    *,
    failed: Failed,
    futures: Futures,
    order: persistence.PendingPairOrder,
) -> Generator[PendingPair, None, None]:
    for pending_pair in persistence.select_pending_pairs(order):
        if not allow_numbers and pending_pair.numeric:
            continue

        if pending_pair in failed:
            continue

        if pending_pair in futures.values():
            continue

        yield pending_pair


def queue_pair(
    executor: ThreadPoolExecutor,
    pending_pair: PendingPair,
    futures: Futures,
    *,
    headers: Headers,
) -> None:
    futures[
        executor.submit(
            api.make_pair_exp_backoff,
            pending_pair,
            headers,
            timeout=5,
        )
    ] = pending_pair


def push_one_future(
    executor: ThreadPoolExecutor,
    futures: Futures,
    *,
    allow_numbers: bool,
    failed: Failed,
    headers: Headers,
    order: persistence.PendingPairOrder,
) -> bool:
    for pending_pair in valid_pending_pairs(
        allow_numbers,
        failed=failed,
        futures=futures,
        order=order,
    ):
        queue_pair(executor, pending_pair, futures, headers=headers)
        return True
    return False


def handle_completed_futures(
    futures: Futures,
    *,
    failed: Failed,
    timeout: float,
) -> Generator[Pair | None, None, None]:
    n_elements, n_pairs = persistence.counts()
    log_line = f"Pairs: {n_pairs:,d}  Elements: {n_elements:,d}"

    for future in as_completed(futures, timeout=timeout):
        pending_pair = futures.pop(future)
        try:
            pair = future.result()
        except TimeoutError:
            print(f"[API TIMED OUT] {pending_pair}".ljust(len(log_line)))
            print(log_line, end="\r")
            failed.add(pending_pair)
            yield None
            continue
        except Exception as e:
            print(f"[API FAILED - {e!r}] {pending_pair}".ljust(len(log_line)))
            print(log_line, end="\r")
            failed.add(pending_pair)
            yield None
            continue

        try:
            persistence.record_pair(pair)
        except Exception as e:
            print(f"[DATABASE FAILED - {e!r}] {pair}".ljust(len(log_line)))
            print(log_line, end="\r")
            failed.add(pending_pair)
            yield None
            continue

        yield pair

        n_elements, n_pairs = persistence.counts()
        log_line = f"Pairs: {n_pairs:,d}  Elements: {n_elements:,d}"

        print(str(pair).ljust(len(log_line)))
        print(log_line, end="\r")


def now() -> float:
    return time.perf_counter()


def scan(allow_numbers: bool, seconds_per_request: float, threads: int) -> None:
    threads = max(threads, 1)

    headers: Headers = cloudflare.get_headers()
    failed: Failed = set()
    futures: Futures = {}

    orders = persistence.PENDING_PAIR_ORDERS.copy()

    with ThreadPoolExecutor(threads) as executor:

        def shutdown() -> None:
            executor.shutdown(False, cancel_futures=True)
            incomplete_futures = [f for f in futures if not f.done()]
            if not incomplete_futures:
                return

            n = len(incomplete_futures)

            before = time.perf_counter()
            print(f"[SHUTTING DOWN] 0/{n} threads terminated...", end="\r")
            for i, _ in enumerate(as_completed(incomplete_futures), 1):
                print(f"[SHUTTING DOWN] {i}/{n} threads terminated...", end="\r")
            duration = 1000 * (time.perf_counter() - before)
            print(f"[SHUTDOWN] {n} thread(s) completed in {duration:.2f} milliseconds.")

        while True:
            if len(futures) < threads * 2:
                pushed = push_one_future(
                    executor,
                    futures,
                    allow_numbers=allow_numbers,
                    failed=failed,
                    headers=headers,
                    order=orders[0],
                )

                if not pushed:
                    if failed:
                        failed.clear()
                        continue

                    if not futures:
                        print("Completed! All possible pairs have been made!")
                        return

            next_future_at = now() + seconds_per_request
            try:
                for pair in handle_completed_futures(
                    futures,
                    failed=failed,
                    timeout=next_future_at - now(),
                ):
                    if not pair or pair.result.name.lower() == "nothing":
                        orders.insert(0, orders.pop())
            except TimeoutError:
                pass
            except:
                shutdown()
                raise

            delay_remaining = next_future_at - now()
            if delay_remaining < 0:
                continue

            try:
                time.sleep(delay_remaining)
            except:
                shutdown()
                raise


if __name__ == "__main__":
    scan(False, 0.25, 8)
