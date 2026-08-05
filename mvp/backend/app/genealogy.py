"""Turns a free-text relation ("Great-grandfather") into a generation offset
relative to the account owner (generation 0), for laying out the family
tree older-to-younger, top to bottom. This is only a fallback guess — an
explicit `parent_ancestor_id` link always wins, because it's the only way
to know a grandparent belongs above one specific parent rather than just
"further up" in general.
"""

_UP_WORDS = ("mother", "father", "mom", "dad", "papa", "mama", "parent", "aunt", "uncle")
_DOWN_WORDS = ("son", "daughter", "child", "nephew", "niece")
_SAME_WORDS = (
    "brother", "sister", "sibling", "cousin", "spouse", "wife", "husband", "self", "me", "myself",
)


def infer_generation(relation: str) -> int:
    r = relation.lower()

    if "grand" in r:
        greats = r.count("great")
        if any(w in r for w in _DOWN_WORDS):
            return -(2 + greats)
        return 2 + greats

    if any(w in r for w in _UP_WORDS):
        return 1
    if any(w in r for w in _DOWN_WORDS):
        return -1
    if any(w in r for w in _SAME_WORDS):
        return 0
    return 0  # unrecognized relation word: assume same generation


def compute_generation(ancestor_id: int, by_id: dict[int, "AncestorLike"]) -> int:  # noqa: F821
    """Walks the explicit parent_ancestor_id chain when present, falling back
    to the relation-word guess at whichever node ends the chain — a root
    (no parent link), a dangling reference, or a cycle. Always bounded:
    each ancestor is visited at most once."""
    node = by_id.get(ancestor_id)
    if node is None:
        return 0

    seen: set[int] = set()
    hops = 0
    current = node
    while current.parent_ancestor_id is not None:
        if current.id in seen:
            break  # cycle — stop and use `current`'s own relation word below
        seen.add(current.id)
        parent = by_id.get(current.parent_ancestor_id)
        if parent is None:
            break  # dangling reference — same fallback
        hops += 1
        current = parent

    # `current` is the root of the chain (oldest ancestor found); the node we
    # started from is `hops` generations YOUNGER than that root.
    return infer_generation(current.relation) - hops
