import time
from base64 import b64encode
from textwrap import dedent

import persistence


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
    dump()
