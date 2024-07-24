from mptt.managers import TreeManager
from unicef_locations.models import AbstractLocation


# TODO: [e44] Fix this. this is a copy from the library deferring geom and point from selection
# hotfix needed due to significant performance issues when loading PDs with 20 + indicators each having 25+ locations
class LocationsManager(TreeManager):

    def get_queryset(self):
        return super().get_queryset().defer("geom", "point", "parent__geom", "parent__point").select_related('parent')

    def active(self):
        return self.get_queryset().filter(is_active=True)

    def archived_locations(self):
        return self.get_queryset().filter(is_active=False)

    def all_with_geom(self):
        return super().get_queryset().select_related('parent')


class Location(AbstractLocation):
    objects = LocationsManager()
