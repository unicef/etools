from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition(".")[0]
    verbose_name = "Last Mile"

    def ready(self):
        from etools.applications.last_mile import signals  # NOQA
