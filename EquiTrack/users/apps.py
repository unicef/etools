from django.apps import AppConfig, apps
from django.conf import settings


class UsersAppConfig(AppConfig):
    name = 'users'

    def ready(self):
        from actstream import registry
        registry.register(apps.get_model(settings.AUTH_USER_MODEL))
