from django.contrib.gis.db.models.functions import Distance

from etools.applications.locations.models import Location


class LocationValidatorService:
    def find_location_for_point(self, point):
        location = Location.objects.all_with_geom().filter(
            geom__contains=point,
            is_active=True
        ).order_by('-admin_level').first()

        if not location:
            location = self._find_nearest_location(point)

        return location

    def _find_nearest_location(self, point):
        return Location.objects.all_with_geom().filter(
            point__isnull=False,
            is_active=True
        ).annotate(
            distance=Distance('point', point)
        ).order_by('distance').first()

    def validate_point_with_borders(self, point):
        location = self.find_location_for_point(point)

        if location:
            return {
                'valid': True,
                'location': location
            }

        return {
            'valid': False,
            'location': None,
            'error': 'No location found for the provided coordinates'
        }
