"""
Organizational unit types.

The main party structure is a strict chain, matching Article 11 of the
NDC Constitution exactly ("The Party shall be organised at branch,
constituency, regional and national level"):
    NATIONAL > REGIONAL > CONSTITUENCY > BRANCH

DISTRICT_COORDINATING_COMMITTEE is real (Article 17) but is explicitly
NOT one of the four constitutional "levels of organisation" - it only
exists in districts containing more than one constituency, has no
conference or elected executive of its own, and its membership is drawn
FROM the constituency executives it coordinates (chairmen, secretaries,
organisers, the MP, two reps per Constituency Executive Committee)
rather than containing them as subordinates. It is modeled as an
auxiliary type for exactly that reason - same as the other auxiliary
bodies below, it attaches via `parent` without being a rung in the
Branch-to-National authority chain.

Auxiliary bodies mirror Article 10's "Integral Organs of the Party":
Youth Wing, Women's Wing, Parliamentary Group, Zongo Caucus, External
Branches, plus "any other integral organs that may be created by the
National Congress" - which is where DISTRICT_COORDINATING_COMMITTEE,
COUNCIL_OF_ELDERS (Article 24) and FUNCTIONAL_COMMITTEE (Article 23,
confirmed real, replicated at Regional/Constituency level "with
necessary modifications" per Article 23(5)) come from: all real, just
not in the fixed Article 10 list itself. PROFESSIONALS_FORUM is the one
type here **not directly confirmed** anywhere in this (mini) constitution's
73 pages - it's a reasonable guess at a Congress-created organ under
Article 10(f), not a citation. Verify against the full constitution if
available. They are tagged with their own unit_type but take their
position in the tree from their `parent` field - e.g. a WOMENS_WING unit
whose parent is a REGIONAL unit *is* that Region's Women's Wing. This
mirrors how the party's own constitution replicates auxiliary structures
alongside the main hierarchy at multiple levels, without hard-coding a
combinatorial explosion of unit types.

TEIN (Tertiary Education Institutions Network) has its own explicit
6-level chain because those level names are specific and fixed. TEIN's
own internal levels below "national" aren't specified in the
constitution's text (which only confirms TEIN's *representation* at
Regional/Youth/Women conferences) - this chain is a reasonable
operational extension, not a constitutional citation, and should be
revisited if the full (non-mini) constitution specifies it differently.
"""

MAIN_CHAIN = [
    "NATIONAL",
    "REGIONAL",
    "CONSTITUENCY",
    "BRANCH",
]

TEIN_CHAIN = [
    "TEIN_NATIONAL",
    "TEIN_REGIONAL",
    "TEIN_CAMPUS",
    "TEIN_FACULTY",
    "TEIN_DEPARTMENT",
    "TEIN_CLASS",
]

AUXILIARY_TYPES = [
    "DISTRICT_COORDINATING_COMMITTEE",
    "WOMENS_WING",
    "YOUTH_WING",
    "ZONGO_CAUCUS",
    "EXTERNAL_BRANCH",
    "PARLIAMENTARY_GROUP",
    "COUNCIL_OF_ELDERS",
    "FUNCTIONAL_COMMITTEE",
    "PROFESSIONALS_FORUM",
]

ALL_UNIT_TYPES = MAIN_CHAIN + TEIN_CHAIN + AUXILIARY_TYPES

UNIT_TYPE_CHOICES = [(t, t.replace("_", " ").title()) for t in ALL_UNIT_TYPES]

# Numeric rank used for authority comparisons within the main chain and
# within the TEIN chain. Lower rank == higher authority. Auxiliary types
# are not globally ranked; their authority is derived from tree ancestry
# (see OrganizationalUnit.is_ancestor_of) plus their own parent's rank.
MAIN_CHAIN_RANK = {unit_type: index for index, unit_type in enumerate(MAIN_CHAIN)}
TEIN_CHAIN_RANK = {unit_type: index for index, unit_type in enumerate(TEIN_CHAIN)}


def expected_parent_type(unit_type: str):
    """Returns the unit_type that should be the parent of `unit_type` within
    a strict chain, or None if `unit_type` is a root or not chain-governed
    (auxiliary units may attach under any main-chain or TEIN unit)."""
    if unit_type in MAIN_CHAIN:
        idx = MAIN_CHAIN.index(unit_type)
        return MAIN_CHAIN[idx - 1] if idx > 0 else None
    if unit_type in TEIN_CHAIN:
        idx = TEIN_CHAIN.index(unit_type)
        return TEIN_CHAIN[idx - 1] if idx > 0 else None
    return None  # auxiliary types: flexible attachment, validated case-by-case
