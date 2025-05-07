from django.db import models
from django.db.models import F

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


class SimplifiedGeomQueryset(models.query.QuerySet):
    def simplified(self):
        sql = "SELECT ST_SimplifyVW(geom, 0.125) AS geom"
        return self.extra(select={'geom': sql})


class SimplifiedGeomManager(models.Manager):
    def get_queryset(self):
        return SimplifiedGeomQueryset(self.model, using=self._db).annotate(parent_pcode=F('parent__p_code'))

    def simplified(self):
        return self.get_queryset().simplified()


class Location(AbstractLocation):

    FIRST_ADMIN_LEVEL = 0  # Country
    SECOND_ADMIN_LEVEL = 1  # Region or Province or County or ...
    THIRD_ADMIN_LEVEL = 2  # Everything under a region
    FOURTH_ADMIN_LEVEL = 3

    objects = LocationsManager()
    simplified_geom = SimplifiedGeomManager()

    def get_parent_locations(self):
        location_data = {}
        current = self
        while current:
            location_data[current.admin_level] = current
            current = current.parent

        return location_data

    def get_parent_locations_with_borders(self):
        location_data = {}
        tolerance = 0.01
        current = self
        while current:
            simplified_geom = None
            if current.geom:
                simplified_geom = current.geom.simplify(tolerance, preserve_topology=True)

            location_data[current.admin_level] = {"location": current.name, "borders": list(simplified_geom.coords) if simplified_geom else []}

            current = current.parent

        return location_data
