from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from unicef_locations.cache import invalidate_cache

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.libraries.views.cache import invalidate_view_cache


@receiver(post_save, sender=LocationSite)
def update_location_site_cache_on_save(instance, created, **kwargs):
    invalidate_cache()
    invalidate_view_cache('fm-sites.{}'.format(connection.tenant.country_short_code or ''))


@receiver(post_delete, sender=LocationSite)
def update_location_site_cache_on_delete(instance, **kwargs):
    invalidate_cache()
    invalidate_view_cache('fm-sites.{}'.format(connection.tenant.country_short_code or ''))
