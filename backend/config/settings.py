import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

IS_TESTING = "pytest" in sys.modules

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key-do-not-use-in-prod")

DEBUG = True if IS_TESTING else os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        "ALLOWED_HOSTS",
        "ndc-platform-production.up.railway.app,healthcheck.railway.app,.railway.app,localhost,127.0.0.1",
    ).split(",")
    if h.strip()
]

for host in [
    "healthcheck.railway.app",
]:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)


INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django_prometheus",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.hierarchy",
    "apps.departments",
    "apps.membership",
    "apps.messaging",
    "apps.elections",
    "apps.events",
    "apps.finance",
    "apps.dashboard",
    "apps.welfare",
    "apps.complaints",
    "apps.documents",
    "apps.donations",
    "apps.volunteers",
    "apps.analytics",
    "apps.media",
    "apps.chatbot",
    "apps.discipline",
    "apps.executive_ai",
    "apps.dues",
]


MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "apps.core.middleware.AuditRequestMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]


ROOT_URLCONF = "config.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "django_internal.sqlite3",
    }
}


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# IS_TESTING forces mongomock unconditionally. This has been reverted to
# a hardcoded real credential and back to a plain env-only default
# multiple times now across direct edits to this file. Tests must never
# be able to reach a real database, no matter what is in .env, and this
# file must never contain a real connection string as a fallback
# default. Real values belong only in an untracked .env file or the
# deployment platform's own environment variables.
if IS_TESTING:
    MONGO_URI = "mongomock://localhost"
    MONGO_DB_NAME = "ndc_test"
else:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ndc_platform")

JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)

JWT_ALGORITHM = "HS256"

JWT_ACCESS_TOKEN_TTL = timedelta(
    minutes=int(os.getenv("JWT_ACCESS_TOKEN_TTL_MINUTES", "30"))
)

JWT_REFRESH_TOKEN_TTL = timedelta(
    days=int(os.getenv("JWT_REFRESH_TOKEN_TTL_DAYS", "7"))
)


REDIS_HOST = os.getenv("REDISHOST", "redis.railway.internal")

REDIS_PORT = os.getenv("REDISPORT", "6379")

REDIS_USER = os.getenv("REDISUSER", "default")

REDIS_PASSWORD = os.getenv("REDISPASSWORD", "")

REDIS_URL = os.getenv(
    "REDIS_URL", f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
)


if IS_TESTING or os.getenv("CACHE_BACKEND") == "locmem":
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            },
        }
    }


CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False").lower() == "true"


if CORS_ALLOW_ALL_ORIGINS:

    CORS_ALLOWED_ORIGINS = []

    CORS_ALLOWED_ORIGIN_REGEXES = []

else:

    default_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://ndc-platform.vercel.app",
    ]

    environment_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")

    if environment_origins:

        from apps.core.cors_utils import normalize_cors_origin

        CORS_ALLOWED_ORIGINS = [
            normalize_cors_origin(origin)
            for origin in environment_origins.split(",")
            if origin.strip()
        ]

    else:

        CORS_ALLOWED_ORIGINS = default_origins

    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://ndc-platform.*\.vercel\.app$",
        r"^https://.*-desward-technology-s-projects\.vercel\.app$",
    ]


CORS_ALLOW_CREDENTIALS = True


CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]


CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": "apps.accounts.documents.AnonymousUser",
    "UNAUTHENTICATED_TOKEN": None,
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "10/min",
        "chat": "20/min",
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}


SPECTACULAR_SETTINGS = {
    "TITLE": "NDC Political Party Management Platform API",
    "DESCRIPTION": (
        "API for the National Democratic Congress hierarchical party "
        "management system."
    ),
    "VERSION": "0.1.0-phase0",
    "SERVE_INCLUDE_SCHEMA": False,
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "ndc": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}


if not DEBUG:

    SECURE_SSL_REDIRECT = True

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/?$"]

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = "DENY"


EMAIL_BACKEND = (
    "django.core.mail.backends.locmem.EmailBackend"
    if IS_TESTING
    else "django.core.mail.backends.smtp.EmailBackend"
)

EMAIL_HOST = os.getenv("EMAIL_HOST", "")

EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")

EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@ndc-platform.example")


TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")


FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# The specific Claude model every AI feature calls (Executive AI tools,
# the chatbot, AI-assisted reporting) - configurable so a model update
# never requires a code change, just a Railway variable update.
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-6")


PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")


SENTRY_DSN = os.getenv("SENTRY_DSN", "")


if SENTRY_DSN and not IS_TESTING:

    import sentry_sdk

    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    )
