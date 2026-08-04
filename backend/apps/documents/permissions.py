def can_manage_documents(user, target_unit) -> bool:
    """Uploading/deleting a document scoped to `target_unit` requires
    "hierarchy.manage", ancestor-scoped like everywhere else."""
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def can_view_document(user, document) -> bool:
    if user.is_superadmin or document.is_public_within_party:
        return True
    if user.organizational_unit is None:
        return False
    # Visible to the document's own unit subtree, and to any ancestor
    # (who by definition has oversight of that unit).
    return document.organizational_unit.is_same_or_ancestor_of(
        user.organizational_unit
    ) or user.organizational_unit.is_same_or_ancestor_of(document.organizational_unit)
