from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):

    def ready(self):
        from . import signals  # NOQA
