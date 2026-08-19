import pytest
from django.core.management import call_command
from mongoengine.errors import NotUniqueError

pytestmark = pytest.mark.django_db


def _make_user(
    email, phone, membership_id, branch_unit, ordinary_role, national_id=None
):
    from apps.accounts.documents import User

    user = User(
        email=email,
        phone_number=phone,
        first_name="Test",
        last_name="User",
        membership_id=membership_id,
        organizational_unit=branch_unit,
        role=ordinary_role,
        national_id_number=national_id,
    )
    user.set_password("StrongPass123!")
    return user


def test_multiple_users_with_no_national_id_number_coexist(branch_unit, ordinary_role):
    """The real bug: MongoEngine writes an explicit `null` for an unset
    optional field rather than omitting the key, so a plain `sparse`
    index (which only excludes truly *missing* keys) never actually
    prevented this collision - confirmed via a real DuplicateKeyError in
    production. The model now uses a partial index instead, with an
    explicit filter expression that genuinely excludes null values."""
    from apps.accounts.documents import User

    _make_user(
        "one@example.com", "0240000001", "NDC-IDX-000001", branch_unit, ordinary_role
    ).save()
    _make_user(
        "two@example.com", "0240000002", "NDC-IDX-000002", branch_unit, ordinary_role
    ).save()
    assert User.objects(national_id_number=None).count() == 2


def test_duplicate_real_national_id_number_is_still_rejected(
    branch_unit, ordinary_role
):
    """The partial index must still do its actual job: two members who
    both really do have the same national ID number on file must still
    be rejected - this isn't just disabling the uniqueness constraint to
    work around the null collision."""
    _make_user(
        "three@example.com",
        "0240000005",
        "NDC-IDX-000005",
        branch_unit,
        ordinary_role,
        national_id="GHA-123456789-0",
    ).save()

    duplicate = _make_user(
        "four@example.com",
        "0240000006",
        "NDC-IDX-000006",
        branch_unit,
        ordinary_role,
        national_id="GHA-123456789-0",
    )
    with pytest.raises(NotUniqueError):
        duplicate.save()


def test_fix_user_indexes_repairs_a_stale_plain_unique_index(
    branch_unit, ordinary_role
):
    """Reproduces the exact production error: a plain (non-partial)
    unique index predating this fix - confirmed to genuinely fail on a
    second null value first, then confirmed the fix command resolves it
    for real - not just asserting the code looks right."""
    from apps.accounts.documents import User

    collection = User._get_collection()
    if "national_id_number_1" in collection.index_information():
        collection.drop_index("national_id_number_1")
    collection.create_index("national_id_number", unique=True)

    _make_user(
        "seven@example.com", "0240000009", "NDC-IDX-000009", branch_unit, ordinary_role
    ).save()

    second = _make_user(
        "eight@example.com", "0240000010", "NDC-IDX-000010", branch_unit, ordinary_role
    )
    with pytest.raises(NotUniqueError):
        second.save()

    call_command("fix_user_indexes")

    second.save()  # must succeed for real now
    assert User.objects(national_id_number=None).count() == 2


def test_fix_user_indexes_command_never_calls_get_collection_directly():
    """Regression guard for the exact bug this command originally shipped
    with: `User._get_collection()` internally triggers MongoEngine's own
    `ensure_indexes()`, which immediately tries to (re)create the new
    partial index while an old, same-named conflicting index still
    exists - throwing IndexKeySpecsConflict *before* this command's own
    drop-the-stale-index logic ever runs. Confirmed against a real
    fresh-process invocation in production (this command's own test
    process didn't reproduce it reliably, since an earlier
    _get_collection() call elsewhere in the same process had already
    made MongoEngine attempt - and in a healthy test database, succeed
    at - creating the index, masking the failure a genuinely first-ever
    call hits against a real pre-existing conflicting index). The
    command must go through mongoengine.connection.get_db() directly,
    which has no such side effect, instead."""
    import inspect

    from apps.core.management.commands import fix_user_indexes

    source = inspect.getsource(fix_user_indexes)
    assert "= User._get_collection()" not in source
    assert "mongoengine.connection.get_db()" in source
