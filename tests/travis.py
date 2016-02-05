DEBUG = True

SECRET_KEY = "unguessable"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "rest_framework.authtoken",
    "redis_pubsub",
    "testapp"
    ]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "travis_ci_test",
        "USER": "postgres",
        "PASSWORD": "",
        "HOST": "localhost",
        }
    }

SITE_ID = 1

REDIS_HOST = "localhost", 6379
