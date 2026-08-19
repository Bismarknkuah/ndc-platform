import mongoengine
from django.core.management.base import BaseCommand

from apps.accounts.documents import User

# These two fields are unique-but-optional (a member may have no
# national ID or voter ID on file yet). A plain `sparse: True` index
# does NOT actually solve this - sparse only excludes documents where
# the key is truly *absent*, but MongoEngine writes an explicit `null`
# for an unset optional field rather than omitting the key entirely, so
# a present key with value null still collides even under a sparse
# index. The fix is a *partial* index instead (see
# apps/accounts/documents.py's current meta.indexes), which uses an
# explicit filter expression to genuinely exclude null values from the
# uniqueness constraint. This command repairs any index that predates
# that fix - whether it was a plain unique index or an (ineffective)
# sparse one - to the current partial definition.
INDEXES_TO_CHECK = ["national_id_number_1", "voter_id_number_1"]


class Command(BaseCommand):
    help = (
        "Fix the national_id_number/voter_id_number unique indexes on an "
        "existing database to use a partial filter expression instead of "
        "(ineffective) sparse - safe to run any time, a no-op if already "
        "correct."
    )

    def handle(self, *args, **options):
        # Deliberately NOT User._get_collection() - that classmethod
        # itself calls MongoEngine's ensure_indexes() internally on
        # first use per process, which immediately tries to create the
        # new partial index while the old, same-named sparse/plain index
        # still exists, throwing IndexKeySpecsConflict *before* this
        # command's own drop logic below ever gets to run - confirmed the
        # hard way against a real fresh-process invocation, where this
        # collision reproduced every time (masked in this command's own
        # test suite, where an earlier _get_collection() call elsewhere
        # in the same test process had already made MongoEngine consider
        # indexes "ensured" and skip re-triggering them - a real gap in
        # that verification, not something to gloss over). Going through
        # the raw pymongo database handle instead has no such side
        # effect.
        db = mongoengine.connection.get_db()
        collection = db[User._get_collection_name()]
        existing = collection.index_information()

        dropped = []
        for index_name in INDEXES_TO_CHECK:
            info = existing.get(index_name)
            if info is None:
                self.stdout.write(f"{index_name}: not present yet, nothing to fix.")
                continue
            if "partialFilterExpression" in info:
                self.stdout.write(
                    self.style.SUCCESS(f"{index_name}: already a partial index, OK.")
                )
                continue
            collection.drop_index(index_name)
            dropped.append(index_name)
            kind = "sparse (ineffective)" if info.get("sparse") else "plain unique"
            self.stdout.write(
                self.style.WARNING(f"{index_name}: was a {kind} index, dropped.")
            )

        # Only now is it safe to let MongoEngine (re)create the indexes -
        # the conflicting old ones, if any, are already gone.
        User.ensure_indexes()

        if dropped:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Recreated {len(dropped)} index(es) as partial. Multiple users "
                    "with no national_id_number/voter_id_number can now coexist."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Nothing needed fixing."))
