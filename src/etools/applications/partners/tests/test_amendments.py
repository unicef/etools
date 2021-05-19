import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention, InterventionAmendment
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    InterventionActivityFactory,
    LowerResultFactory,
    ReportingRequirementFactory,
)
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
            end=today + datetime.timedelta(days=365),
            status=Intervention.ACTIVE,
            date_sent_to_partner=today - datetime.timedelta(days=1),
            signed_by_unicef_date=today - datetime.timedelta(days=1),
            signed_by_partner_date=today - datetime.timedelta(days=1),
            unicef_signatory=self.unicef_staff,
            partner_authorized_officer_signatory=self.partner1.staff_members.all().first()
        )
        ReportingRequirementFactory(intervention=self.active_intervention)

        self.result_link = InterventionResultLinkFactory(
            intervention=self.active_intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        self.pd_output = LowerResultFactory(result_link=self.result_link)
        self.activity = InterventionActivityFactory(result=self.pd_output)

        self.amendment_defaults = dict(
            intervention=self.active_intervention,
            types=[InterventionAmendment.TYPE_ADMIN_ERROR],
            signed_date=timezone.now().date() - datetime.timedelta(days=1),
            signed_amendment=SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8'))
        )

    def test_start_amendment(self):
        amendment = InterventionAmendment.objects.create(**self.amendment_defaults)
        self.assertIsNotNone(amendment.amended_intervention)
        self.assertEqual(amendment.intervention.signed_date, amendment.amended_intervention.signed_date)

    def test_quarters_update(self):
        self.activity.time_frames.add(*self.active_intervention.quarters.filter(quarter__in=[1, 3]))
        amendment = InterventionAmendment.objects.create(**self.amendment_defaults)

        activity = amendment.intervention.result_links.first().ll_results.first().activities.first()
        activity_copy = amendment.amended_intervention.result_links.first().ll_results.first().activities.first()
        self.assertListEqual(list(activity_copy.time_frames.values_list('quarter', flat=True)), [1, 3])
        activity_copy.time_frames.remove(*amendment.amended_intervention.quarters.filter(quarter=1))
        activity_copy.time_frames.add(*amendment.amended_intervention.quarters.filter(quarter__in=[2, 4]))

        amendment.merge_amendment()

        self.assertListEqual(list(activity.time_frames.values_list('quarter', flat=True)), [2, 3, 4])
