from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Partners'

    def ready(self):
        from etools.applications.partners import signals  # noqa
