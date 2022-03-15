from django.apps import AppConfig


class LocationsConfig(AppConfig):
    name = __name__.rpartition('.')[0]
    print(name)
    verbose_name = 'Locations'
