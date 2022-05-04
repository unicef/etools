from django.apps import AppConfig


class TravelAppConfig(AppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Travel'
