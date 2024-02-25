# Infinite Craft Explorer
This code simply iterates through every possible combination of elements, and saves their pairings to your file system.

It provides three exploration strategies:
- `random` Simply grabs two random elements and tests their pairing.
- `depth` Prioritizes using newly-found elements. The goal is to arrive at new discoveries faster.
- `breadth` Makes pairs in alphabetical order. The goal is to achieve wide coverage before getting any "specific" pairings.

[`persistence.py`](./persistence.py) is responsible for determining how results are saved. For my purposes, it's was 
most convenient to browse pairings via the File Explorer, so right now it saves results like this:
```
Water/
├── Water  # file containing "Lake"
├── Earth  # file containing "Plant"
└── ...
Fire/
├── Earth  # file containing "Lava"
├── Wind   # file containing "Smoke"
└── ... 
.../
```
but this code could _easily_ be refactored to support a more sophisticated persistence, like a database. PRs welcome.