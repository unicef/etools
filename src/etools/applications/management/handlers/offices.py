from etools.applications.action_points.models import ActionPoint
from etools.applications.management.handlers.base import SimpleHandler
from etools.applications.partners.models import Intervention
from etools.applications.t2f.models import Travel
from etools.applications.tpm.models import TPMActivity
from etools.applications.users.models import Country, Office, UserProfile


class OfficeHandler(SimpleHandler):

    model = Office

    queryset_migration_mapping = (
        (Country.objects.all(), 'offices'),
        (UserProfile.objects.all(), 'office'),
        (Intervention.objects.all(), 'offices'),
        (Travel.objects.all(), 'office'),
        (TPMActivity.objects.all(), 'offices'),
        (ActionPoint.objects.all(), 'office'),
    )
