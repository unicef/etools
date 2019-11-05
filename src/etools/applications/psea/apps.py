from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'PSEA'

    def ready(self):
        from etools.applications.psea import signals  # noqa
