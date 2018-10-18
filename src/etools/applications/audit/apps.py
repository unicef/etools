
from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Auditor Portal'

    def ready(self):
        from etools.applications.audit import signals  # NOQA
