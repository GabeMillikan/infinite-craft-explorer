from pathlib import Path

from pair import Pair

directory = Path(__file__).parent / "knowledge"
directory.mkdir(exist_ok=True)


def encode_invalid_name(name: str) -> str:
    return f"_{name.encode('utf-8').hex()}"


def decode_name(name: str) -> str:
    if name.startswith("_"):
        if name.startswith("__"):
            return name[1:]
        return bytes.fromhex(name[1:]).decode("utf-8")
    return name


def load_all() -> tuple[set[str], set[Pair]]:
    known_elements: set[str] = set()
    known_pairs: set[Pair] = set()

    for first_known_element in directory.iterdir():
        for second_known_element in first_known_element.iterdir():
            with second_known_element.open() as f:
                result = f.read()

            known_elements.add(decode_name(first_known_element.name))
            known_elements.add(decode_name(second_known_element.name))
            known_elements.add(result)

            known_pairs.add(
                Pair(
                    decode_name(first_known_element.name),
                    decode_name(second_known_element.name),
                    result,
                ),
            )

    return known_elements, known_pairs


def record_known_element(name: str) -> Path:
    try:
        d = directory / f"_{name}" if name.startswith("_") else directory / name
        d.mkdir(exist_ok=True)
    except OSError:
        d = directory / encode_invalid_name(name)
        d.mkdir(exist_ok=True)

    return d


def record_pair(pair: Pair) -> None:
    assert pair.output is not None

    first_dir = record_known_element(pair.inputs[0])
    second_name = record_known_element(pair.inputs[1]).name
    record_known_element(pair.output)

    with (first_dir / second_name).open("w") as f:
        f.write(pair.output)
