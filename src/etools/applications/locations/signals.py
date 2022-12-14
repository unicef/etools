from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from unicef_locations.cache import invalidate_cache

from etools.applications.locations.models import Location
from etools.libraries.views.cache import invalidate_view_cache


@receiver(post_save, sender=Location)
def update_location_cache_on_save(instance, created, **kwargs):
    invalidate_cache()
    invalidate_view_cache('locations.{}'.format(connection.tenant.country_short_code or ''))


@receiver(post_delete, sender=Location)
def update_location_cache_on_delete(instance, **kwargs):
    invalidate_cache()
    invalidate_view_cache('locations.{}'.format(connection.tenant.country_short_code or ''))
