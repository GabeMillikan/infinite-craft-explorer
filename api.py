import time

from curl_cffi import requests

from models import Element, Pair, PendingPair


def raw_make_pair(
    first: str,
    second: str,
    headers: dict[str, str],
) -> tuple[str, str | None, bool | None]:
    response = requests.get(
        "https://neal.fun/api/infinite-craft/pair",
        {"first": first, "second": second},
        headers=headers,
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
) -> Pair:
    result, emoji, is_new = raw_make_pair(pair.first.name, pair.second.name, headers)
    return Pair(
        pair.first,
        pair.second,
        Element(result, emoji),
        is_new,
    )


def make_pair_exp_backoff(
    pair: PendingPair,
    headers: dict[str, str],
) -> Pair:
    backoff = 1
    while True:
        try:
            return make_pair(pair, headers)
        except Exception as e:
            print(
                f"Failed to compute {pair}: {e}\n"
                f"Trying again in {backoff} second(s)",
            )
            time.sleep(backoff)
            backoff *= 2
            backoff = min(backoff, 60)


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
