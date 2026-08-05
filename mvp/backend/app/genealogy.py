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

    if "in-law" in r or "in law" in r:
        # "Son-in-law", "daughter-in-law", etc. describe a marriage, not a
        # blood generation — the base word (son/daughter/...) doesn't say
        # what generation they married into. An explicit spouse link is the
        # correct way to place them; without one, default to the same
        # generation as a neutral guess rather than misreading the word.
        return 0

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
    """Walks parent links (one generation older per hop) and spouse links
    (same generation, no hop) until reaching a node with neither — a root,
    a dangling reference, or a cycle — then applies that node's own
    relation-word guess as the base. Always bounded: each ancestor is
    visited at most once, so a mutual spouse link or a parent cycle can't
    loop forever.

    Parent is checked before spouse at every step, deliberately: a person's
    own recorded parents are more authoritative than transitively borrowing
    a generation through whoever they married. Spouse is only a fallback
    for someone who married in with no parents of their own on record —
    it should never override a person's own, perfectly good parent link."""
    node = by_id.get(ancestor_id)
    if node is None:
        return 0

    seen: set[int] = set()
    hops = 0
    current = node
    while current.id not in seen:
        seen.add(current.id)

        if current.parent_ancestor_id is not None and current.parent_ancestor_id in by_id:
            hops += 1
            current = by_id[current.parent_ancestor_id]
            continue

        if current.spouse_ancestor_id is not None and current.spouse_ancestor_id in by_id:
            current = by_id[current.spouse_ancestor_id]
            continue

        break  # no more links — this is the root the guess is based on

    # `current` is the root of the chain; the node we started from is
    # `hops` generations YOUNGER than that root (spouse hops don't count).
    return infer_generation(current.relation) - hops
