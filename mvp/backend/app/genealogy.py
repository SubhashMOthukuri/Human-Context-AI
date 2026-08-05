"""Turns a free-text relation ("Great-grandfather") into a generation offset
relative to the account owner (generation 0), for laying out the family
tree older-to-younger, top to bottom. This is only a fallback guess — an
explicit `parent_ancestor_id` or `spouse_ancestor_id` link always wins,
because it's the only way to know a grandparent belongs above one specific
parent (or a wife belongs beside her husband, not below him) rather than
just "somewhere near" in general.
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
    """Walks spouse links (same generation, no hop) and parent links (one
    generation older per hop) until reaching a node with neither — a root,
    a dangling reference, or a cycle — then applies that node's own
    relation-word guess as the base. Always bounded: each ancestor is
    visited at most once, so a mutual spouse link or a parent cycle can't
    loop forever."""
    node = by_id.get(ancestor_id)
    if node is None:
        return 0

    seen: set[int] = set()
    hops = 0
    current = node
    while current.id not in seen:
        seen.add(current.id)

        if current.spouse_ancestor_id is not None and current.spouse_ancestor_id in by_id:
            current = by_id[current.spouse_ancestor_id]
            continue

        if current.parent_ancestor_id is not None and current.parent_ancestor_id in by_id:
            hops += 1
            current = by_id[current.parent_ancestor_id]
            continue

        break  # no more links — this is the root the guess is based on

    # `current` is the root of the chain; the node we started from is
    # `hops` generations YOUNGER than that root (spouse hops don't count).
    return infer_generation(current.relation) - hops
