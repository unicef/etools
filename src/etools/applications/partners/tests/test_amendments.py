import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention, InterventionAmendment
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import ReportingRequirementFactory
from etools.applications.users.tests.factories import UserFactory


class AmendmentTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        self.unicef_staff = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        self.pme = UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])

        self.partner1 = PartnerFactory(name='Partner 2')
        self.active_agreement = AgreementFactory(
            partner=self.partner1,
            status='active',
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today()
        )

        self.active_intervention = InterventionFactory(
            agreement=self.active_agreement,
            title='Active Intervention',
            document_type=Intervention.PD,
            start=today - datetime.timedelta(days=1),
            end=today + datetime.timedelta(days=90),
            status=Intervention.ACTIVE,
            date_sent_to_partner=today - datetime.timedelta(days=1),
            signed_by_unicef_date=today - datetime.timedelta(days=1),
            signed_by_partner_date=today - datetime.timedelta(days=1),
            unicef_signatory=self.unicef_staff,
            partner_authorized_officer_signatory=self.partner1.staff_members.all().first()
        )
        ReportingRequirementFactory(intervention=self.active_intervention)

    def test_start_amendment(self):
        amendment = InterventionAmendment.objects.create(
            intervention=self.active_intervention,
            types=[InterventionAmendment.TYPE_ADMIN_ERROR],
            signed_date=timezone.now().date() - datetime.timedelta(days=1),
            signed_amendment=SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8'))
        )
        print(amendment.intervention)
        print(amendment.amended_intervention)
