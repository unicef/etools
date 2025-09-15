from dataclasses import dataclass

from django.db import connection
from django.db.models import QuerySet

from unicef_locations.cache import invalidate_cache

from etools.applications.core.models import BulkDeactivationLog
from etools.applications.locations.models import Location
from etools.libraries.views.cache import invalidate_view_cache


@dataclass
class DeactivateLocationsResult:
    deactivated_count: int


class LocationsDeactivationService:

    def deactivate(self, locations: QuerySet[Location], *, actor=None) -> DeactivateLocationsResult:
        to_update = locations.filter(is_active=True)
        ids = list(to_update.values_list("id", flat=True))
        updated = to_update.update(is_active=False)
        if updated:
            BulkDeactivationLog.objects.create(
                user=actor,
                affected_ids=ids,
                affected_count=updated,
                model_name="Location",
                app_label="locations",
            )
            try:
                invalidate_cache()
            finally:
                invalidate_view_cache('locations.{}'.format(connection.tenant.country_short_code or ''))
        return DeactivateLocationsResult(deactivated_count=updated)
