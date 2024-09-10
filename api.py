import time

from curl_cffi import requests

from models import Element, Pair, PendingPair


def raw_make_pair(
    first: str,
    second: str,
    headers: dict[str, str],
    *,
    timeout: float = 30,
) -> tuple[str, str | None, bool | None]:
    response = requests.get(
        "https://neal.fun/api/infinite-craft/pair",
        {"first": first, "second": second},
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()

    if "result" not in data:
        msg = f"Invalid response: {data!r}"
        raise ValueError(msg)

    return data["result"], data.get("emoji"), data.get("isNew")


def make_pair(
    pair: PendingPair,
    headers: dict[str, str],
    *,
    timeout: float = 30,
) -> Pair:
    result, emoji, is_new = raw_make_pair(
        pair.first.name,
        pair.second.name,
        headers,
        timeout=timeout,
    )
    return Pair(
        pair.first,
        pair.second,
        Element(result, emoji),
        is_new,
    )


def make_pair_exp_backoff(
    pair: PendingPair,
    headers: dict[str, str],
    *,
    timeout: float = 30,
) -> Pair:
    started_at = time.perf_counter()
    backoff = 1
    while True:
        exc = None
        try:
            eta = timeout - (time.perf_counter() - started_at)
            return make_pair(pair, headers, timeout=eta)
        except requests.RequestsError as e:
            if e.args and e.args[0].startswith("HTTP Error 500:"):
                raise  # don't bother retrying
            exc = e
        except Exception as e:
            exc = e

        eta = timeout - (time.perf_counter() - started_at)
        if eta < backoff:
            msg = f"Ran out of time while making the pair: {pair}"
            raise TimeoutError(msg) from exc

        time.sleep(backoff)
        backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    import cloudflare

    headers = cloudflare.get_headers()

    pair = make_pair(
        PendingPair(
            Element(input("First Element: ")),
            Element(input("Second Element: ")),
        ),
        headers,
    )

    print(pair)
