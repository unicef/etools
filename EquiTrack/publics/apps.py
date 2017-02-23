from django.apps import AppConfig


class PublicsAppConfig(AppConfig):
    name = 'publics'

    # def ready(self):
    #     from actstream import registry
    #     registry.register(self.get_model('Agreement'))