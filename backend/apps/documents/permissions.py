def can_manage_documents(user, target_unit) -> bool:
    """Uploading/deleting a document scoped to `target_unit` requires
    "hierarchy.manage", ancestor-scoped like everywhere else - OR
    holding HEAD/DEPUTY_HEAD of any department at this unit or an
    ancestor of it, since a real department head (Communications
    Director being the clearest case) genuinely needs to upload the
    department's own documents without also needing the broader
    hierarchy.manage a Chairman carries."""
    if user.is_superadmin:
        return True
    if user.role and "hierarchy.manage" in (user.role.permissions or []):
        if (
            user.organizational_unit
            and user.organizational_unit.is_same_or_ancestor_of(target_unit)
        ):
            return True
    from apps.departments.permissions import has_any_department_authority

    return has_any_department_authority(user, target_unit)


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
