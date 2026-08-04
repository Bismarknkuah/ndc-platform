import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger("ndc")


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "NDC Core"

    def ready(self):
        import mongoengine

        # Avoid double-connecting under the dev autoreloader / test runner.
        if "default" in mongoengine.connection._connections:
            return

        connect_kwargs = {
            "db": settings.MONGO_DB_NAME,
            "host": settings.MONGO_URI,
            "alias": "default",
        }

        # Test suites point MONGO_URI at "mongomock://localhost" to run
        # against an in-memory Mongo-compatible database with zero
        # external dependencies. Real deployments use a mongodb(+srv)://
        # Atlas URI and take the branch below untouched.
        if settings.MONGO_URI.startswith("mongomock://"):
            import mongomock

            connect_kwargs["host"] = "localhost"
            connect_kwargs["mongo_client_class"] = mongomock.MongoClient

        mongoengine.connect(**connect_kwargs)
        logger.info("Connected to MongoDB database '%s'", settings.MONGO_DB_NAME)
