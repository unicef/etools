from django.apps import AppConfig


class LocationsConfig(AppConfig):
    name = __name__.rpartition('.')[0]
    verbose_name = 'Locations'
