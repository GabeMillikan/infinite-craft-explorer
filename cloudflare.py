import contextlib
import json
import re
from pathlib import Path

import pyperclip

import api


def parse_curl_string(curl_string: str) -> dict[str, str]:
    headers = {}
    header_lines = curl_string.strip().splitlines()

    for header_line in header_lines:
        found = re.search(r"-H\s*'(.*?)\s*:\s*(.*)'", header_line)
        if not found:
            continue

        headers[found.group(1)] = found.group(2)

    return headers


def prompt_for_headers() -> dict[str, str]:
    while True:
        print(
            "Follow these directions to bypass CloudFlare anti-bot restrictions.\n"
            "  1. Go to https://neal.fun/infinite-craft/\n"
            "  2. Open the developer tools, and select the Network tab\n"
            "  3. Make any pair\n"
            "  4. In the Network tab, find the network request that was made (search 'pair')\n"
            "  5. Right click on it -> Copy -> Copy as cURL (bash)\n"
            "  6. Come back to the terminal, and press 'Enter'.",
        )
        input()
        curl_string = pyperclip.paste()
        if curl_string.startswith(
            "curl 'https://neal.fun/api/infinite-craft/pair?first=",
        ):
            headers = parse_curl_string(curl_string)
            if headers:
                return headers

        print(
            "Hmm... it doesn't look like your clipboard contains the right data. Try again.\n\n",
        )


def verify_headers(headers: dict[str, str]) -> Exception | None:
    try:
        api.raw_make_pair("Fire", "Water", headers)
    except Exception as e:
        return e

    return None


def get_headers(verify: bool = True) -> dict[str, str]:
    filename = Path(__file__).parent / ".cloudflare-headers-cache.json"
    try:
        with filename.open() as f:
            headers = json.load(f)
    except Exception:
        pass
    else:
        if not verify or verify_headers(headers):
            return headers

        with contextlib.suppress(Exception):
            filename.unlink()

    headers = prompt_for_headers()
    if verify:
        error = verify_headers(headers)
        if error is not None:
            print(f"Those headers are not valid! Error: {error!r}")
            print("Try again.\n")
            return get_headers(verify)

    with contextlib.suppress(Exception), filename.open("w") as f:
        json.dump(headers, f, indent=2)

    return headers


if __name__ == "__main__":
    headers = get_headers()
    print("Your (working) headers:")
    print(json.dumps(headers, indent=2))
