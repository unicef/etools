from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.field_monitoring.fm_settings.views import LocationSitesViewSet


@receiver(post_save, sender=LocationSite)
def update_location_site_receiver(instance, created, **kwargs):
    LocationSitesViewSet.list.invalidate()
