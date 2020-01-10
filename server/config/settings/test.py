from .base import *  # noqa

DEBUG = False

TEMPLATES[0]["OPTIONS"]["debug"] = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST_NAME": ":memory:"
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# Use fast password hasher so tests run faster
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

TEST_RUNNER = "config.runner.PytestTestRunner"
