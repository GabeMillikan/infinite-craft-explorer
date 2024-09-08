import json
from textwrap import dedent

import persistence


def dump() -> None:
    data = [
        (element.emoji, element.name, discovered)
        for element, discovered in persistence.select_elements_and_discovered()
    ]

    print(
        dedent(
            f"""
            let data = {json.dumps(data)};
            let storage = JSON.parse(localStorage.getItem("infinite-craft-data")) || {{}};
            storage.elements = storage.elements || [];

            const nameSet = new Set(storage.elements.map(element => element.text));

            data.forEach(element => {{
                let [emoji, name, discovered] = element;

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
