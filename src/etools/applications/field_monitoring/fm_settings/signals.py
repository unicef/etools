from django.db.models.signals import post_save
from django.dispatch import receiver

from unicef_locations.cache import invalidate_cache

from etools.applications.field_monitoring.fm_settings.models import LocationSite


@receiver(post_save, sender=LocationSite)
def update_location_site_receiver(instance, created, **kwargs):
    # LocationSitesViewSet.list.invalidate()
    invalidate_cache()
