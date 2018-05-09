
from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Action Points'

    def ready(self):
        from . import checks  # noqa
        from etools.config.celery import app  # noqa
