class Pair:
    def __init__(self, a: str, b: str, result: str | None = None) -> None:
        self.inputs = (a, b) if a < b else (b, a)
        self.output = result

    def __hash__(self) -> int:
        return hash(self.inputs)

    def __eq__(self, other: "Pair") -> bool:
        return self.inputs == other.inputs

    def __str__(self) -> str:
        return f"{self.inputs[0]!r} + {self.inputs[1]!r} = {self.output!r}"
