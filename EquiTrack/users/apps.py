from django.apps import AppConfig, apps


class UsersAppConfig(AppConfig):
    name = 'users'

    def ready(self):
        from actstream import registry
        registry.register(apps.get_model('auth.User'))
