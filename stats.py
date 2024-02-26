import persistence as p

with p.connect() as conn:
    (discoveries,) = conn.execute(
        "SELECT COUNT(*) FROM pair WHERE pair.is_discovery",
    ).fetchone()
    (pairs,) = conn.execute("SELECT COUNT(*) FROM pair").fetchone()
    (elements,) = conn.execute("SELECT COUNT(*) FROM element").fetchone()

    print(f"- Performed {pairs} element combinations (pairs).")
    print(f"- Found {elements} elements.")
    print(f"- Discovered {discoveries} new elements.")

    result = conn.execute(
        """
            SELECT first.emoji || ' ' || first.name,
                   second.emoji || ' ' || second.name,
                   result.emoji || ' ' || result.name
              FROM pair
        INNER JOIN element AS first ON first.id = pair.first_element_id
        INNER JOIN element AS second ON second.id = pair.second_element_id
        INNER JOIN element AS result ON result.id = pair.result_element_id
             WHERE pair.is_discovery
        """,
    )

    print("- New Discoveries:")
    for row in result:
        first, second, result = row
        print(f"    - {first} + {second} = {result}")
