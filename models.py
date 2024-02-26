import re


class Element:
    def __init__(
        self,
        name: str,
        emoji: str | None = None,
        database_id: int | None = None,
    ) -> None:
        self.name = name
        self.emoji = emoji or "\N{BLACK QUESTION MARK ORNAMENT}"
        self.database_id = database_id

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: "Element") -> bool:
        return self.name == other.name

    def __str__(self) -> str:
        return f"{self.emoji} {self.name}"

    def __repr__(self) -> str:
        return repr(str(self))

    @property
    def numeric(self) -> bool:
        return re.search(r"\d", self.name) is None


class PendingPair:
    def __init__(self, first: Element, second: Element) -> None:
        self.first, self.second = (
            (first, second) if first.name < second.name else (second, first)
        )

    def __hash__(self) -> int:
        return hash((self.first, self.second))

    def __eq__(self, other: "Pair") -> bool:
        return self.first == other.first and self.second == other.second

    def __str__(self) -> str:
        return f"{self.first} + {self.second}"

    def __repr__(self) -> str:
        return f"{self.first!r} + {self.second!r}"

    @property
    def numeric(self) -> bool:
        return self.first.numeric or self.second.numeric


class Pair(PendingPair):
    def __init__(
        self,
        first: Element,
        second: Element,
        result: Element,
        is_discovery: bool | None = None,
    ) -> None:
        super().__init__(first, second)
        self.result = result
        self.is_discovery = is_discovery is True

    def __str__(self) -> str:
        addendum = " (New Discovery!)" if self.is_discovery else ""
        return f"{super().__str__()} = {self.result}{addendum}"

    def __repr__(self) -> str:
        addendum = " (New Discovery!)" if self.is_discovery else ""
        return f"{super().__repr__()} = {self.result!r}{addendum}"

    @property
    def elements(self) -> tuple[Element, Element, Element]:
        return self.first, self.second, self.result
