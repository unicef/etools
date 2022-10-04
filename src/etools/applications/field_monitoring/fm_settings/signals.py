from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse

from etools.applications.field_monitoring.fm_settings.models import LocationSite


@receiver(post_save, sender=LocationSite)
def update_location_site_cache_on_save(instance, created, **kwargs):
    from etools.applications.field_monitoring.fm_settings.views import LocationSitesViewSet
    LocationSitesViewSet.invalidate_view_cache(reverse('field_monitoring_settings:sites-list'))


@receiver(post_delete, sender=LocationSite)
def update_location_site_cache_on_delete(instance, **kwargs):
    from etools.applications.field_monitoring.fm_settings.views import LocationSitesViewSet
    LocationSitesViewSet.invalidate_view_cache(reverse('field_monitoring_settings:sites-list'))
