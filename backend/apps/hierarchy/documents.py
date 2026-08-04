from mongoengine import (
    BooleanField,
    DictField,
    FloatField,
    ReferenceField,
    StringField,
)

from apps.core.documents import TimestampedDocument
from apps.hierarchy.constants import UNIT_TYPE_CHOICES


class OrganizationalUnit(TimestampedDocument):
    """
    A single node in the party's organizational tree. Covers the main
    chain (National -> Branch), TEIN's six levels, and every auxiliary
    body. The tree is expressed purely via `parent`, which keeps the
    model uniform regardless of which sub-structure a node belongs to.
    """

    name = StringField(required=True, max_length=200)
    code = StringField(
        required=True, unique=True, max_length=64
    )  # e.g. "ndc-national", "gh-ashanti-region"
    unit_type = StringField(required=True, choices=UNIT_TYPE_CHOICES)

    parent = ReferenceField("self", null=True, default=None)

    # Free-form structured data specific to the unit type, e.g.
    # {"region_capital": "Kumasi"} or {"university": "KNUST"} for a
    # TEIN_CAMPUS unit, without needing a new collection per unit type.
    metadata = DictField(default=dict)

    # Optional GIS coordinates for map plotting (e.g. a Branch/polling
    # station's physical location). Both must be set together or not at
    # all - validated in the serializer, not here.
    latitude = FloatField(null=True, min_value=-90, max_value=90)
    longitude = FloatField(null=True, min_value=-180, max_value=180)

    is_active = BooleanField(default=True)

    meta = {
        "collection": "organizational_units",
        "indexes": [
            "unit_type",
            "parent",
            {"fields": ["code"], "unique": True},
        ],
        "ordering": ["name"],
    }

    def __str__(self):
        return f"{self.name} ({self.unit_type})"

    # ------------------------------------------------------------------
    # Tree helpers
    # ------------------------------------------------------------------
    def get_ancestors(self):
        """Returns ancestors ordered from immediate parent up to the root."""
        ancestors = []
        node = self.parent
        while node is not None:
            ancestors.append(node)
            node = node.parent
        return ancestors

    def get_children(self):
        return OrganizationalUnit.objects(parent=self, is_active=True)

    def get_descendants(self):
        """Breadth-first collection of every descendant unit."""
        descendants = []
        frontier = list(self.get_children())
        while frontier:
            descendants.extend(frontier)
            next_frontier = []
            for node in frontier:
                next_frontier.extend(node.get_children())
            frontier = next_frontier
        return descendants

    def is_ancestor_of(self, other: "OrganizationalUnit") -> bool:
        return self in other.get_ancestors()

    def is_same_or_ancestor_of(self, other: "OrganizationalUnit") -> bool:
        return self.id == other.id or self.is_ancestor_of(other)
