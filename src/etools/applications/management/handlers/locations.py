from unicef_locations.models import Location

from etools.applications.action_points.models import ActionPoint
from etools.applications.management.handlers.base import ABCHandler
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity
from etools.applications.tpm.models import TPMActivity


class LocationHandler(ABCHandler):

    model = Location

    queryset_migration_mapping = (
        (Intervention.objects.all(), 'flat_locations'),
        (AppliedIndicator.objects.all(), 'locations'),
        (TravelActivity.objects.all(), 'locations'),
        (TPMActivity.objects.all(), 'locations'),
        (ActionPoint.objects.all(), 'location')
    )
