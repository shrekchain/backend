import os
from celery import Celery
from django.apps import apps, AppConfig
from django.conf import settings

if not settings.configured:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "config.settings.base"
    )  # pragma: no cover


app = Celery("helios")


class CeleryConfig(AppConfig):
    name = "taskapp"
    verbose_name = "Celery Config"

    def ready(self):
        # Using a string here means the worker will not have to
        # pickle the object when using Windows.
        app.config_from_object("django.conf:settings", namespace="CELERY")
        installed_apps = [app_config.name for app_config in apps.get_app_configs()]
        app.autodiscover_tasks(lambda: installed_apps, force=True)


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))  # pragma: no cover
