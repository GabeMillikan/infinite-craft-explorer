import random
import sqlite3
from typing import Generator

from models import Element, Pair, PendingPair


def connect() -> sqlite3.Connection:
    return sqlite3.connect("cache.sqlite")


with connect() as conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS element (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            name TEXT UNIQUE,
            emoji TEXT
        )
        """,
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pair (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            first_element_id INTEGER,
            second_element_id INTEGER,
            result_element_id INTEGER,
            is_discovery INTEGER,
            FOREIGN KEY (first_element_id) REFERENCES element (id),
            FOREIGN KEY (second_element_id) REFERENCES element (id),
            FOREIGN KEY (result_element_id) REFERENCES element (id)
            UNIQUE(first_element_id, second_element_id)
        )
        """,
    )


def _upsert_element(conn: sqlite3.Connection, element: Element) -> None:
    conn.execute(
        """
        INSERT INTO element (name, emoji)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET
        emoji = excluded.emoji
        """,
        (element.name, element.emoji),
    )

    (element.database_id,) = conn.execute(
        "SELECT id FROM element WHERE name = ?",
        (element.name,),
    ).fetchone()


def _upsert_pair(conn: sqlite3.Connection, pair: Pair) -> None:
    # first, insert the elements:
    for element in pair.elements:
        if element.database_id is not None:
            continue

        _upsert_element(conn, element)

    # now, record the pair:
    conn.execute(
        """
        INSERT INTO pair (first_element_id, second_element_id, result_element_id, is_discovery)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(first_element_id, second_element_id) DO UPDATE SET
        result_element_id = excluded.result_element_id,
        is_discovery = MAX(is_discovery, excluded.is_discovery)
        """,
        (*(e.database_id for e in pair.elements), 1 if pair.is_discovery else 0),
    )


def record_pair(pair: Pair) -> None:
    with connect() as conn:
        _upsert_pair(conn, pair)


def _select_pending_pairs(
    conn: sqlite3.Connection,
) -> Generator[PendingPair, None, None]:
    order = random.choice(
        (
            "first.id DESC, second.id DESC",
            "first.id ASC, second.id DESC",
            "first.id ASC, second.id ASC",
        ),
    )

    result = conn.execute(
        f"""
        SELECT
            first.id,
            first.name,
            first.emoji,
            second.id,
            second.name,
            second.emoji
        FROM element AS first
        LEFT JOIN element AS second ON first.name <= second.name
        LEFT JOIN pair ON pair.first_element_id = first.id AND pair.second_element_id = second.id
        WHERE pair.id IS NULL
        ORDER BY {order}
        """,
    )

    for row in result:
        first_id, first_name, first_emoji, second_id, second_name, second_emoji = row

        yield PendingPair(
            Element(first_name, first_emoji, first_id),
            Element(second_name, second_emoji, second_id),
        )


def select_pending_pairs() -> Generator[PendingPair, None, None]:
    with connect() as conn:
        yield from _select_pending_pairs(conn)


def _element_count(conn: sqlite3.Connection) -> int:
    (count,) = conn.execute("SELECT COUNT(*) FROM element").fetchone()
    return count


def _pair_count(conn: sqlite3.Connection) -> int:
    (count,) = conn.execute("SELECT COUNT(*) FROM pair").fetchone()
    return count


def counts() -> tuple[int, int]:
    with connect() as conn:
        return _element_count(conn), _pair_count(conn)


def _select_elements_and_discovered(
    conn: sqlite3.Connection,
) -> Generator[tuple[Element, bool], None, None]:
    result = conn.execute(
        """
        SELECT
            e.name,
            e.emoji,
            e.id,
            MAX(p.result_element_id IS NOT NULL) AS is_discovery
        FROM element e
        LEFT JOIN pair p
            ON p.result_element_id = e.id
            AND p.is_discovery = TRUE
        GROUP BY e.name, e.emoji, e.id
        ORDER BY e.id ASC
        """,
    )

    for row in result:
        *e, is_discovery = row

        yield Element(*e), is_discovery


def select_elements_and_discovered() -> Generator[tuple[Element, bool], None, None]:
    with connect() as conn:
        return _select_elements_and_discovered(conn)


with connect() as conn:
    primary_elements = [
        Element("Fire", "\N{FIRE}"),
        Element("Earth", "\N{EARTH GLOBE EUROPE-AFRICA}"),
        Element("Water", "\N{DROPLET}"),
        Element("Wind", "\N{WIND BLOWING FACE}\N{VARIATION SELECTOR-16}"),
    ]

    # The search order is "mostly deterministic" on the macroscopic scale
    # so randomize the order of the primary elements so that everyone who runs
    # this code gets one of 4! (factorial) possible "macroscopic routes"
    random.shuffle(primary_elements)

    for e in primary_elements:
        _upsert_element(conn, e)
