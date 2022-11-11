import datetime
import json
from decimal import Decimal
from unittest import skip
from unittest.mock import Mock, patch

from django.db import connection
from django.test import override_settings, SimpleTestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from unicef_snapshot.models import Activity

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory
from etools.applications.field_monitoring.planning.tests.factories import (
    MonitoringActivityFactory,
    MonitoringActivityGroupFactory,
)
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import (
    Assessment,
    CoreValuesAssessment,
    Intervention,
    InterventionAmendment,
    OrganizationType,
    PartnerOrganization,
    PartnerPlannedVisits,
)
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    AssessmentFactory,
    InterventionFactory,
    PartnerFactory,
    PartnerPlannedVisitsFactory,
)
from etools.applications.partners.views.partner_organization_v2 import PartnerOrganizationAddView
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    ResultFactory,
    ResultTypeFactory,
    SectionFactory,
)
from etools.applications.t2f.tests.factories import TravelActivityFactory
from etools.applications.users.tests.factories import UserFactory
from etools.libraries.pythonlib.datetime import get_quarter

INSIGHT_PATH = "etools.applications.partners.tasks.get_data_from_insight"


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('partner-assessment', 'assessments/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/partners/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestPartnerOrganizationListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("partners_api:partner-list")

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        PartnerFactory()
        PartnerFactory()
        response = self.forced_auth_req(
            'get', self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_lead_section(self):
        section = SectionFactory()
        partner = PartnerFactory(lead_section=section)
        PartnerFactory()
        response = self.forced_auth_req(
            'get', self.url,
            user=self.unicef_staff,
            QUERY_STRING=f'lead_section={section.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], partner.id)


class TestPartnerOrganizationDetailAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                organization_type=OrganizationType.GOVERNMENT,
                cso_type="International",
                vendor_number="DDD",
                short_name="Short name",
            ),
            hidden=False,
        )
        agreement = AgreementFactory(
            partner=cls.partner,
            signed_by_unicef_date=datetime.date.today())

        cls.intervention = InterventionFactory(
            agreement=agreement,
            status=Intervention.CLOSED
        )
        cls.file_type = AttachmentFileTypeFactory()

        cls.url = reverse(
            "partners_api:partner-detail",
            kwargs={'pk': cls.partner.pk}
        )

    def test_get_partner_details(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff
        )
        data = json.loads(response.rendered_content)
        self.assertEqual(self.intervention.pk, data["interventions"][0]["id"])

    def test_patch_with_core_values_assessment_attachment(self):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        assessment_qs = CoreValuesAssessment.objects.filter(
            partner=self.partner
        )
        self.assertFalse(assessment_qs.exists())
        response = self.forced_auth_req(
            'patch',
            self.url,
            data={
                "core_values_assessments": [{
                    "attachment": attachment.pk
                }]
            },
            user=self.unicef_staff
        )
        data = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["id"], self.partner.pk)
        self.assertEqual(data["interventions"][0]["id"], self.intervention.pk)
        self.assertTrue(assessment_qs.exists())
        self.assertEqual(len(data["core_values_assessments"]), 1)
        self.assertEqual(
            data["core_values_assessments"][0]["attachment"],
            attachment.file.url
        )

    def test_patch_with_assessment_attachment(self):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        assessment_qs = Assessment.objects.filter(
            partner=self.partner
        )
        self.assertFalse(assessment_qs.exists())
        response = self.forced_auth_req(
            'patch',
            self.url,
            data={
                "assessments": [{
                    "report_attachment": attachment.pk,
                    "completed_date": datetime.date.today(),
                    "type": Assessment.TYPE_OTHER,
                }]
            },
            user=self.unicef_staff
        )
        data = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["id"], self.partner.pk)
        self.assertEqual(data["interventions"][0]["id"], self.intervention.pk)
        self.assertTrue(assessment_qs.exists())
        self.assertEqual(len(data["assessments"]), 1)
        self.assertEqual(
            data["assessments"][0]["report_attachment"],
            attachment.file.url
        )

    def test_add_planned_visits(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 0)

        planned_visits = [{
            "year": datetime.date.today().year,
            "programmatic_q1": 1,
            "programmatic_q2": 2,
            "programmatic_q3": 3,
            "programmatic_q4": 4,
        }]
        data = {
            "name": self.partner.name + ' Updated',
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "planned_visits": planned_visits,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 1)
        self.assertEqual(
            response.data["planned_visits"][0]["year"],
            datetime.date.today().year
        )

    def test_update_planned_visits(self):
        planned_visit = PartnerPlannedVisitsFactory(
            partner=self.partner,
            year=datetime.date.today().year,
            programmatic_q1=1,
            programmatic_q2=2,
            programmatic_q3=3,
            programmatic_q4=4,
        )
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 1)
        data = response.data["planned_visits"][0]
        self.assertEqual(data["programmatic_q1"], 1)
        self.assertEqual(data["programmatic_q2"], 2)
        self.assertEqual(data["programmatic_q3"], 3)
        self.assertEqual(data["programmatic_q4"], 4)

        planned_visits = [{
            "id": planned_visit.pk,
            "year": planned_visit.year,
            "programmatic_q1": 4,
            "programmatic_q2": 3,
            "programmatic_q3": 2,
            "programmatic_q4": 1,
        }]
        data = {
            "name": self.partner.name + ' Updated',
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "planned_visits": planned_visits,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 1)
        data = response.data["planned_visits"][0]
        self.assertEqual(data["programmatic_q1"], 4)
        self.assertEqual(data["programmatic_q2"], 3)
        self.assertEqual(data["programmatic_q3"], 2)
        self.assertEqual(data["programmatic_q4"], 1)

    def test_update_planned_visits_no_id(self):
        """Ensure update happens if no id value provided"""
        planned_visit = PartnerPlannedVisitsFactory(
            partner=self.partner,
            year=datetime.date.today().year,
            programmatic_q1=1,
            programmatic_q2=2,
            programmatic_q3=3,
            programmatic_q4=4,
        )
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 1)
        data = response.data["planned_visits"][0]
        self.assertEqual(data["programmatic_q1"], 1)
        self.assertEqual(data["programmatic_q2"], 2)
        self.assertEqual(data["programmatic_q3"], 3)
        self.assertEqual(data["programmatic_q4"], 4)

        planned_visits = [{
            "year": planned_visit.year,
            "programmatic_q1": 4,
            "programmatic_q2": 3,
            "programmatic_q3": 2,
            "programmatic_q4": 1,
        }]
        data = {
            "name": self.partner.name + ' Updated',
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "planned_visits": planned_visits,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 1)
        data = response.data["planned_visits"][0]
        self.assertEqual(data["programmatic_q1"], 4)
        self.assertEqual(data["programmatic_q2"], 3)
        self.assertEqual(data["programmatic_q3"], 2)
        self.assertEqual(data["programmatic_q4"], 1)

    def test_update_planned_visits_no_year(self):
        """Ensure update happens if no id value provided"""
        current_year = datetime.date.today().year
        planned_visit = PartnerPlannedVisitsFactory(
            partner=self.partner,
            year=current_year,
            programmatic_q1=1,
            programmatic_q2=2,
            programmatic_q3=3,
            programmatic_q4=4,
        )
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 1)
        data = response.data["planned_visits"][0]
        self.assertEqual(data["programmatic_q1"], 1)
        self.assertEqual(data["programmatic_q2"], 2)
        self.assertEqual(data["programmatic_q3"], 3)
        self.assertEqual(data["programmatic_q4"], 4)

        planned_visits = [{
            "programmatic_q1": 4,
            "programmatic_q2": 3,
            "programmatic_q3": 2,
            "programmatic_q4": 1,
        }]
        data = {
            "name": self.partner.name + ' Updated',
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "planned_visits": planned_visits,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["planned_visits"]), 1)
        data = response.data["planned_visits"][0]
        self.assertEqual(data["id"], planned_visit.pk)
        self.assertEqual(data["year"], current_year)
        self.assertEqual(data["programmatic_q1"], 4)
        self.assertEqual(data["programmatic_q2"], 3)
        self.assertEqual(data["programmatic_q3"], 2)
        self.assertEqual(data["programmatic_q4"], 1)

    def test_validation_fail_non_government(self):
        """Ensure update happens if no id value provided"""
        current_year = datetime.date.today().year
        cso_partner = PartnerFactory(
            organization=OrganizationFactory(
                organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION,
                cso_type="International",
                vendor_number="XYZ",
                short_name="City Hunter",
            ),
            hidden=False,
        )

        PartnerPlannedVisitsFactory(
            partner=cso_partner,
            year=current_year,
            programmatic_q1=1,
            programmatic_q2=2,
            programmatic_q3=3,
            programmatic_q4=4,
        )
        planned_visits = [{
            "programmatic_q1": 4,
            "programmatic_q2": 3,
            "programmatic_q3": 2,
            "programmatic_q4": 1,
        }]
        data = {
            "name": cso_partner.name + ' Updated',
            "partner_type": cso_partner.partner_type,
            "vendor_number": cso_partner.vendor_number,
            "planned_visits": planned_visits,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[cso_partner.pk]),
            user=self.unicef_staff,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["planned_visits"]["partner"],
                         ErrorDetail(string='Planned Visit can be set only for Government partners', code='invalid'))

    @skip('AMP-REALM: To be removed')
    def test_update_staffmember_inactive(self):
        partner_staff_user = UserFactory(is_staff=True, realms__data=[])
        response = self.forced_auth_req(
            "patch",
            self.url,
            data={
                "staff_members": [{
                    "id": partner_staff_user.pk,
                    "email": partner_staff_user.email,
                    "active": False,
                }],
            },
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_update_staffmember_invalid_email(self):
    #     partner_staff_user = UserFactory(is_staff=True, realms__data=[])
    #     partner_staff = PartnerStaffFactory(
    #         partner=self.partner,
    #         user=partner_staff_user,
    #     )
    #     response = self.forced_auth_req(
    #         "patch",
    #         self.url,
    #         data={
    #             "staff_members": [{
    #                 "id": partner_staff.pk,
    #                 "email": partner_staff.email.upper(),
    #             }],
    #         },
    #         user=self.unicef_staff,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(
    #         response.data['staff_members']['email'][0],
    #         'User emails cannot be changed, please remove the user and add another one: {}'.format(
    #             partner_staff.email.upper(),
    #         ),
    #     )
    #
    # def test_update_staffmember_inactive_prp_synced_from_intervention(self):
    #     partner_staff_user = UserFactory(is_staff=True, realms__data=[])
    #     partner_staff = PartnerStaffFactory(partner=self.partner, user=partner_staff_user, active=True)
    #     agreement = AgreementFactory(
    #         status=Agreement.SIGNED,
    #         partner=self.partner,
    #     )
    #     agreement.authorized_officers.add(partner_staff)
    #     intervention = InterventionFactory(
    #         status=Intervention.SIGNED,
    #         agreement=agreement,
    #     )
    #     intervention.partner_focal_points.add(partner_staff)
    #     self.assertIn(partner_staff, intervention.partner_focal_points.all())
    #     self.assertIn(partner_staff, agreement.authorized_officers.all())
    #     response = self.forced_auth_req(
    #         "patch", self.url,
    #         data={
    #             "staff_members": [{
    #                 "id": partner_staff.pk,
    #                 "email": partner_staff.email,
    #                 "active": False,
    #             }]
    #         },
    #         user=self.unicef_staff,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(
    #         response.data['staff_members']['active'][0],
    #         'User already synced to PRP and cannot be disabled. '
    #         'Please instruct the partner to disable from PRP'
    #     )
    #
    # def test_update_staff_member_already_active_in_other_tenant(self):
    #     staff_mock = Mock(return_value=Country(name='fake country', id=-1))
    #
    #     partner_staff = PartnerStaffFactory(
    #         email='test@example.com',
    #         active=False,
    #         user__email='test@example.com',
    #     )
    #     with patch('etools.applications.users.models.User.get_staff_member_country', staff_mock):
    #         response = self.forced_auth_req(
    #             "patch", self.url,
    #             data={
    #                 "staff_members": [{
    #                     "id": partner_staff.pk,
    #                     "email": partner_staff.email,
    #                     "active": True,
    #                 }]
    #             },
    #             user=self.unicef_staff,
    #         )
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
    #     self.assertEqual(
    #         response.data['staff_members']['active'][0],
    #         'The Partner Staff member you are trying to activate is associated '
    #         'with a different Partner Organization'
    #     )

    @skip('AMP-REALM: To be removed')
    def test_assign_staff_member_creates_new_user(self):
        self.assertEqual(self.partner.staff_members.count(), 1)
        staff_email = "email@staff.com"
        response = self.forced_auth_req(
            "patch", self.url,
            data={"staff_members": [{"email": staff_email, "active": True, 'first_name': 'First', 'last_name': 'Last'}]},
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.partner.staff_members.count(), 2)
        created_staff = self.partner.staff_members.get(email=staff_email)
        self.assertEqual(created_staff.first_name, created_staff.user.first_name)
        self.assertEqual(created_staff.last_name, created_staff.user.last_name)

    @skip('AMP-REALM: To be removed')
    def test_assign_staff_member_to_existing_user(self):
        user = UserFactory(realms__data=[], is_staff=False)

        response = self.forced_auth_req(
            "patch", self.url,
            data={"staff_members": [{"email": user.email, "active": True, 'first_name': 'mr', 'last_name': 'smith'}]},
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNotNone(user.get_partner())
        self.assertTrue(user.profile.countries_available.filter(id=connection.tenant.id).exists())

    @skip('AMP-REALM: To be removed')
    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_assign_staff_member_to_unicef_user(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "patch", self.url,
            data={"staff_members": [{"email": user.email, "active": True, 'first_name': 'mr', 'last_name': 'smith'}]},
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(
            'Unable to associate staff member to UNICEF user',
            response.data['staff_members']['non_field_errors'],
        )

    @skip('AMP-REALM: To be removed')
    def test_assign_staff_member_to_another_staff(self):
        user = UserFactory(realms__data=[], is_staff=False)
        # PartnerStaffFactory(user=user)
        response = self.forced_auth_req(
            "patch", self.url,
            data={"staff_members": [{"email": user.email, "active": True, 'first_name': 'mr', 'last_name': 'smith'}]},
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(
            'The email for the partner contact is used by another partner contact. '
            'Email has to be unique to proceed {}'.format(user.email),
            response.data['staff_members']['active'],
        )

    def test_get_partner_monitoring_activity_groups(self):
        activity1 = MonitoringActivityFactory(partners=[self.partner])
        activity2 = MonitoringActivityFactory(partners=[self.partner])
        activity3 = MonitoringActivityFactory(partners=[self.partner])
        MonitoringActivityGroupFactory(
            partner=self.partner,
            monitoring_activities=[activity1, activity2]
        )
        MonitoringActivityGroupFactory(
            partner=self.partner,
            monitoring_activities=[activity3]
        )
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.data['monitoring_activity_groups'], [[activity1.id, activity2.id], [activity3.id]])

    def _add_hact_finding_for_activity(self, activity):
        ActivityQuestionOverallFinding.objects.create(
            activity_question=ActivityQuestionFactory(
                monitoring_activity=activity,
                question__is_hact=True,
                question__level='partner',
            ),
            value=True
        )
        ActivityOverallFinding.objects.create(
            narrative_finding='ok',
            monitoring_activity=activity,
            partner=self.partner,
        )

    def test_add_partner_monitoring_activity_groups(self):
        today = datetime.date.today()
        activity1 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        activity2 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        self._add_hact_finding_for_activity(activity1)
        self._add_hact_finding_for_activity(activity2)

        self.partner.update_programmatic_visits()
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff)
        self.assertEqual(response.data['hact_values']['programmatic_visits']['completed'][get_quarter()], 2)

        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data={
                'monitoring_activity_groups': [[activity1.id, activity2.id]],
            }
        )
        self.assertEqual(len(response.data['monitoring_activity_groups']), 1)
        self.assertCountEqual(response.data['monitoring_activity_groups'][0], [activity1.id, activity2.id])
        self.assertEqual(response.data['hact_values']['programmatic_visits']['completed'][get_quarter()], 1)

    def test_add_partner_monitoring_activity_into_group(self):
        today = datetime.date.today()
        activity1 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        activity2 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        activity3 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        self._add_hact_finding_for_activity(activity1)
        self._add_hact_finding_for_activity(activity2)
        self._add_hact_finding_for_activity(activity3)

        MonitoringActivityGroupFactory(partner=self.partner, monitoring_activities=[activity1, activity2])

        self.partner.update_programmatic_visits()
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff)
        self.assertEqual(response.data['hact_values']['programmatic_visits']['completed'][get_quarter()], 2)

        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data={
                'monitoring_activity_groups': [[activity1.id, activity2.id, activity3.id]],
            }
        )
        self.assertEqual(len(response.data['monitoring_activity_groups']), 1)
        self.assertCountEqual(response.data['monitoring_activity_groups'][0],
                              [activity1.id, activity2.id, activity3.id])
        self.assertEqual(response.data['hact_values']['programmatic_visits']['completed'][get_quarter()], 1)

    def test_add_partner_monitoring_activity_groups_not_completed_or_not_hact(self):
        activity1 = MonitoringActivityFactory(partners=[self.partner], status='completed')
        activity2 = MonitoringActivityFactory(partners=[self.partner], status='report_finalization')
        activity3 = MonitoringActivityFactory(partners=[self.partner], status='completed')
        self._add_hact_finding_for_activity(activity1)
        self._add_hact_finding_for_activity(activity2)

        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data={
                'monitoring_activity_groups': [[activity1.id, activity2.id, activity3.id]],
            }
        )
        self.assertEqual(len(response.data['monitoring_activity_groups']), 1)
        self.assertEqual(response.data['monitoring_activity_groups'], [[activity1.id]])

    def test_update_partner_monitoring_activity_groups(self):
        today = datetime.date.today()
        activity1 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        activity2 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        activity3 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        activity4 = MonitoringActivityFactory(partners=[self.partner], end_date=today, status='completed')
        self._add_hact_finding_for_activity(activity1)
        self._add_hact_finding_for_activity(activity2)
        self._add_hact_finding_for_activity(activity3)
        self._add_hact_finding_for_activity(activity4)
        MonitoringActivityFactory(partners=[self.partner])

        MonitoringActivityGroupFactory(
            partner=self.partner,
            monitoring_activities=[activity1, activity2]
        )
        MonitoringActivityGroupFactory(
            partner=self.partner,
            monitoring_activities=[activity3, activity4]
        )
        self.partner.update_programmatic_visits()
        # 2 groups
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff)
        self.assertEqual(response.data['hact_values']['programmatic_visits']['completed'][get_quarter()], 2)

        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data={
                'monitoring_activity_groups': [[activity2.id, activity4.id]],
            }
        )
        self.assertEqual(len(response.data['monitoring_activity_groups']), 1)
        self.assertCountEqual(response.data['monitoring_activity_groups'][0], [activity2.id, activity4.id])
        self.assertEqual(self.partner.monitoring_activity_groups.count(), 1)
        self.partner.refresh_from_db()
        # 1 group + 2 ungrouped
        self.assertEqual(response.data['hact_values']['programmatic_visits']['completed'][get_quarter()], 3)


class TestPartnerOrganizationHactAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("partners_api:partner-hact")
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            total_ct_cp=10.00,
            total_ct_cy=8.00,
        )

    def test_get(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        self.assertIn('id', response_json[0].keys())
        self.assertEqual(response_json[0]['id'], self.partner.pk)


class TestPartnerOrganizationAddView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("partners_api:partner-add")
        cls.user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )

    def setUp(self):
        super().setUp()
        self.view = PartnerOrganizationAddView.as_view()

    def test_no_vendor_number(self):
        response = self.forced_auth_req(
            'post',
            self.url,
            data={},
            view=self.view
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"error": "No vendor number provided for Partner Organization"}
        )

    def test_no_insight_reponse(self):
        mock_insight = Mock(return_value=(False, "The vendor number could not be found in INSIGHT"))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=123".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "The vendor number could not be found in INSIGHT"})

    def test_vendor_exists(self):
        PartnerFactory(organization=OrganizationFactory(vendor_number="321"))
        mock_insight = Mock(return_value=(True, {
            "ROWSET": {
                "ROW": {
                    'VENDOR_CODE': '321',
                    'PARTNER_TYPE_DESC': 'Test',
                    'VENDOR_NAME': 'Vendor',
                    'COUNTRY': 'Italy',
                    'TOTAL_CASH_TRANSFERRED_CP': 2000,
                    'TOTAL_CASH_TRANSFERRED_CY': 1000,
                    'NET_CASH_TRANSFERRED_CY': 500,
                    'REPORTED_CY': 250,
                    'TOTAL_CASH_TRANSFERRED_YTD': 125
                }
            }
        }))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=321".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data)

    def test_missing_required_keys(self):
        mock_insight = Mock(return_value=(True, {
            "ROWSET": {
                "ROW": {
                    "VENDOR_CODE": "321",
                }
            }
        }))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=321".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"error": "Partner skipped because one or more of the required fields are missing"}
        )

    def test_invalid_partner_type(self):
        vendor_number = "321"
        mock_insight = Mock(return_value=(True, {
            "ROWSET": {
                "ROW": {
                    "PARTNER_TYPE_DESC": "SOMETHING INVALID",
                    "VENDOR_CODE": vendor_number,
                    "VENDOR_NAME": "New Partner",
                    "CSO_TYPE": "National NGO",
                    "CORE_VALUE_ASSESSMENT_DT": "01-Jan-01",
                    'TOTAL_CASH_TRANSFERRED_CP': "2,000",
                    'TOTAL_CASH_TRANSFERRED_CY': "2,000",
                    'NET_CASH_TRANSFERRED_CY': "2,000",
                    'TOTAL_CASH_TRANSFERRED_YTD': "2,000",
                    'REPORTED_CY': "2,000",
                    "COUNTRY": "239",
                    "MARKED_FOR_DELETION": 'true',
                    "POSTING_BLOCK": 'true',
                }
            }
        }))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=321".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        qs = PartnerOrganization.objects.filter(vendor_number=vendor_number)
        self.assertTrue(qs.exists())
        partner = qs.first()
        self.assertEqual(partner.hidden, True)
        self.assertEqual(partner.blocked, True)
        self.assertEqual(partner.deleted_flag, True)

    def test_post(self):
        self.assertFalse(
            PartnerOrganization.objects.filter(name="New Partner").exists()
        )
        mock_insight = Mock(return_value=(True, {
            "ROWSET": {
                "ROW": {
                    "VENDOR_CODE": "321",
                    "VENDOR_NAME": "New Partner",
                    "PARTNER_TYPE_DESC": "UN AGENCY",
                    "CSO_TYPE": "National NGO",
                    "CORE_VALUE_ASSESSMENT_DT": "01-Jan-01",
                    'TOTAL_CASH_TRANSFERRED_CP': "2,000",
                    'TOTAL_CASH_TRANSFERRED_CY': "2,000",
                    'NET_CASH_TRANSFERRED_CY': "2,000",
                    'TOTAL_CASH_TRANSFERRED_YTD': "2,000",
                    'REPORTED_CY': "2,000",
                    "COUNTRY": "239",
                    "TYPE_OF_ASSESSMENT": "HIGH RISK ASSUMED",
                    "DATE_OF_ASSESSMENT": "20-Jan-20",
                    "MARKED_FOR_DELETION": False,
                    "POSTING_BLOCK": False,
                    "PSEA_ASSESSMENT_DATE": "03-Jan-22",
                    "SEA_RISK_RATING_NAME": "Test",
                    "SEARCH_TERM1": "Search Term",
                }
            }
        }))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=321".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        qs = PartnerOrganization.objects.filter(name="New Partner")
        self.assertTrue(qs.exists())
        partner = qs.first()
        self.assertEqual(partner.partner_type, OrganizationType.UN_AGENCY)
        self.assertEqual(partner.cso_type, "National")
        self.assertEqual(partner.total_ct_cp, None)
        self.assertEqual(
            partner.core_values_assessment_date,
            datetime.date(2001, 1, 1)
        )


class TestPartnerOrganizationDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION,
                cso_type="International",
                vendor_number="DDD",
                short_name="Short name"
            ),
            hidden=False,
        )
        cls.url = reverse(
            'partners_api:partner-delete',
            args=[cls.partner.pk]
        )

    def test_delete_with_signed_agreements(self):
        # create draft agreement with partner
        AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today()
        )
        AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            attached_agreement=None,
            status='draft'
        )

        # should have 1 signed and 1 draft agreement with self.partner
        self.assertEqual(self.partner.agreements.count(), 2)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0],
            "There was a PCA/SSFA signed with this partner or a transaction "
            "was performed against this partner. The Partner record cannot be deleted"
        )
        self.assertTrue(
            PartnerOrganization.objects.filter(pk=self.partner.pk).exists()
        )

    def test_delete_with_draft_agreements(self):
        # create draft agreement with partner
        AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            attached_agreement=None,
            status='draft'
        )
        self.assertEqual(self.partner.agreements.count(), 1)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PartnerOrganization.objects.filter(pk=self.partner.pk).exists()
        )

    def test_delete(self):
        partner = PartnerFactory()
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:partner-delete', args=[partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PartnerOrganization.objects.filter(pk=partner.pk).exists()
        )

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:partner-delete', args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_with_trips(self):
        TravelActivityFactory(partner=self.partner)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0],
            "This partner has trips associated to it"
        )
        self.assertTrue(
            PartnerOrganization.objects.filter(pk=self.partner.pk).exists()
        )

    def test_delete_with_cash_trxs(self):
        partner = PartnerFactory(total_ct_cp=20.00)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:partner-delete', args=[partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0],
            "This partner has cash transactions associated to it"
        )
        self.assertTrue(
            PartnerOrganization.objects.filter(pk=partner.pk).exists()
        )


class TestPartnerPlannedVisitsDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        cls.partner = PartnerFactory()
        cls.planned_visit = PartnerPlannedVisitsFactory(
            partner=cls.partner,
        )
        cls.url = reverse(
            "partners_api:partner-planned-visits-del",
            args=[cls.planned_visit.pk]
        )

    def test_delete(self):
        self.assertTrue(PartnerPlannedVisits.objects.filter(
            pk=self.planned_visit.pk
        ).exists())
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PartnerPlannedVisits.objects.filter(
            pk=self.planned_visit.pk
        ).exists())

    def test_delete_permission(self):
        user = UserFactory()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            'delete',
            reverse("partners_api:partner-planned-visits-del", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestPartnerOrganizationAssessmentUpdateDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.organization = OrganizationFactory(
            organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            vendor_number="DDD",
            short_name="Short name"
        )
        cls.partner = PartnerFactory(organization=cls.organization, hidden=False)
        cls.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[PARTNERSHIP_MANAGER_GROUP],
            profile__organization=cls.organization
        )
        cls.partner_staff = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.organization
        )

    def setUp(self):
        self.assessment = AssessmentFactory(
            partner=self.partner,
            completed_date=None,
            report=None,
        )
        AttachmentFileTypeFactory(code="partners_assessment_report")
        self.attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )

    def test_post(self):
        assessment_qs = Assessment.objects.filter(partner=self.partner)
        assessment_count = assessment_qs.count()
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:partner-assessment'),
            user=self.partnership_manager_user,
            data={
                "partner": self.partner.pk,
                "type": Assessment.TYPE_OTHER,
                "report_attachment": self.attachment.pk,
                "completed_date": datetime.date.today(),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(assessment_qs.count(), assessment_count + 1)
        self.attachment.refresh_from_db()
        self.assertTrue(self.attachment.file_type)

    def test_patch(self):
        self.assertTrue(self.assessment.active)
        response = self.forced_auth_req(
            'patch',
            reverse(
                'partners_api:partner-assessment-detail',
                args=[self.assessment.pk]
            ),
            user=self.partnership_manager_user,
            data={
                "active": False
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assessment.refresh_from_db()
        self.assertFalse(self.assessment.active)

    def test_patch_permission(self):
        response = self.forced_auth_req(
            'patch',
            reverse(
                'partners_api:partner-assessment-detail',
                args=[self.assessment.pk]
            ),
            user=self.unicef_staff,
            data={
                "active": False
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_valid(self):
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners_api:partner-assessment-detail',
                args=[self.assessment.pk]
            ),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_error_completed_date(self):
        assessment = AssessmentFactory(
            partner=self.partner,
            report=None,
        )
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners_api:partner-assessment-detail',
                args=[assessment.pk]
            ),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete a completed assessment"])

    def test_delete_error_report(self):
        assessment = AssessmentFactory(
            partner=self.partner,
            completed_date=None,
        )
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners_api:partner-assessment-detail',
                args=[assessment.pk]
            ),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete a completed assessment"])

    def test_delete_permission(self):
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners_api:partner-assessment-detail',
                args=[self.assessment.pk]
            ),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners_api:partner-assessment-detail',
                args=[404]
            ),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestPartnerOrganizationRetrieveUpdateDeleteViews(BaseTenantTestCase):
    """Exercise the retrieve, update, and delete views for PartnerOrganization"""
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                name='Partner',
                organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION,
                cso_type="International",
                vendor_number="DDD",
                short_name="Short name",
            ),
            hidden=False,
        )

        report = "report.pdf"
        cls.assessment1 = Assessment.objects.create(
            partner=cls.partner,
            type="Micro Assessment"
        )
        cls.assessment2 = Assessment.objects.create(
            partner=cls.partner,
            type="Micro Assessment",
            report=report,
            completed_date=datetime.date.today()
        )

        cls.partner_gov = PartnerFactory(
            organization=OrganizationFactory(organization_type=OrganizationType.GOVERNMENT))

        agreement = AgreementFactory(
            partner=cls.partner,
            signed_by_unicef_date=datetime.date.today())

        cls.intervention = InterventionFactory(
            agreement=agreement,
            status=Intervention.DRAFT,
        )
        cls.output_res_type = ResultTypeFactory(name=ResultType.OUTPUT)

        cls.result = ResultFactory(
            result_type=cls.output_res_type,)

        cls.partnership_budget = cls.intervention.planned_budget
        cls.amendment = InterventionAmendment.objects.create(
            intervention=cls.intervention,
            types=[InterventionAmendment.RESULTS]
        )

        cls.cp = CountryProgrammeFactory(__sequence=10)
        cls.cp_output = ResultFactory(result_type=cls.output_res_type)

    def test_api_partners_update_with_members(self):
        self.assertFalse(Activity.objects.exists())
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 1)
        self.assertEqual(response.data["staff_members"][0]["first_name"], "Mace")

        staff_members = [{
            "title": "Some title",
            "first_name": "John",
            "last_name": "Doe",
            "email": "a@example.com",
            "active": True,
        }]
        data = {
            "name": self.partner.name + ' Updated',
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "staff_members": staff_members,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 2)

        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

    def test_api_partners_update_with_members_exists(self):
        self.assertFalse(Activity.objects.exists())
        detail_response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail_response.data["staff_members"]), 1)
        self.assertEqual(detail_response.data["staff_members"][0]["first_name"], "Mace")

        staff_members = [{
            "title": "Some title",
            "first_name": "John",
            "last_name": "Doe",
            "email": detail_response.data["staff_members"][0]["email"],
            "active": True,
        }]
        data = {
            "name": self.partner.name + ' Updated',
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "staff_members": staff_members,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {
                "staff_members": {
                    "active": [
                        ErrorDetail(
                            string=(
                                "The email for the partner contact is used by another partner contact. "
                                "Email has to be unique to proceed {}"
                            ).format(detail_response.data["staff_members"][0]["email"]),
                            code="invalid"
                        )
                    ]
                }
            },
        )

    def test_api_partners_update_invalid_basis_for_type_of_assessment(self):
        data = {
            "type_of_assessment": PartnerOrganization.HIGH_RISK_ASSUMED,
            "basis_for_risk_rating": "NOT NULL VALUE",
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = [
            ErrorDetail(string='The basis for risk rating has to be blank if Type is Low or High', code='invalid')]
        self.assertEqual(response.data, {
            "basis_for_risk_rating": error})

    def test_api_partners_update_assessments_invalid(self):
        self.assertFalse(Activity.objects.exists())
        today = datetime.date.today()
        assessments = [{
            "id": self.assessment2.id,
            "completed_date": datetime.date(today.year + 1, 1, 1),
        }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"assessments":
                                         {"completed_date": ["The Date of Report cannot be in the future"]}})
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            0
        )

    def test_api_partners_update_assessments_longago(self):
        self.assertFalse(Activity.objects.exists())
        today = datetime.date.today()
        assessments = [{
            "id": self.assessment2.id,
            "completed_date": datetime.date(today.year - 3, 1, 1),
        }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

    def test_api_partners_update_assessments_today(self):
        self.assertFalse(Activity.objects.exists())
        completed_date = datetime.date.today()
        assessments = [{
            "id": self.assessment2.id,
            "completed_date": completed_date,
        }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

    def test_api_partners_update_assessments_yesterday(self):
        self.assertFalse(Activity.objects.exists())
        completed_date = datetime.date.today() - datetime.timedelta(days=1)
        assessments = [{
            "id": self.assessment2.id,
            "completed_date": completed_date,
        }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

    def test_api_partners_update_with_members_empty_phone(self):
        self.assertFalse(Activity.objects.exists())
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 1)
        self.assertEqual(response.data["staff_members"][0]["first_name"], "Mace")

        staff_members = [{
            "title": "Some title",
            "first_name": "John",
            "last_name": "Doe",
            "email": "a1@a.com",
            "active": True,
            "phone": ''
        }]
        data = {
            "staff_members": staff_members,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["staff_members"][1]["phone"], '')
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

    def test_api_partners_update_assessments_tomorrow(self):
        self.assertFalse(Activity.objects.exists())
        completed_date = datetime.date.today() + datetime.timedelta(days=1)
        assessments = [{
            "id": self.assessment2.id,
            "completed_date": completed_date,
        }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"assessments":
                                         {"completed_date": ["The Date of Report cannot be in the future"]}})
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            0
        )

    def test_api_partners_retrieve(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("vendor_number", response.data.keys())
        self.assertIn("address", response.data.keys())
        self.assertIn("Partner", response.data["name"])
        self.assertEqual(['audits', 'programmatic_visits', 'spot_checks'],
                         sorted(response.data['hact_min_requirements'].keys()))
        self.assertEqual(['assurance_coverage', 'audits', 'outstanding_findings', 'programmatic_visits', 'spot_checks'],
                         sorted(response.data['hact_values'].keys()))
        self.assertCountEqual(
            ['completed', 'minimum_requirements'],
            response.data['hact_values']['audits'].keys())
        self.assertEqual(response.data['interventions'], [])

    def test_api_partners_retreive_actual_fr_amounts(self):
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        fr_header_1 = FundsReservationHeaderFactory(intervention=self.intervention)
        fr_header_2 = FundsReservationHeaderFactory(intervention=self.intervention)

        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["interventions"][0]["actual_amount"]),
                         Decimal(fr_header_1.actual_amt_local + fr_header_2.actual_amt_local))

    def test_api_partners_retreive_same_fr_amounts(self):
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        fr_header_1 = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=Decimal("300.00"),
            actual_amt=Decimal("250.00"),
            outstanding_amt=Decimal("200.00"),
            total_amt_local=Decimal("100.00"),
            actual_amt_local=Decimal("50.00"),
            outstanding_amt_local=Decimal("20.00"),
            intervention_amt=Decimal("10.00"),
        )
        fr_header_2 = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=Decimal("300.00"),
            actual_amt=Decimal("250.00"),
            outstanding_amt=Decimal("200.00"),
            total_amt_local=Decimal("100.00"),
            actual_amt_local=Decimal("50.00"),
            outstanding_amt_local=Decimal("20.00"),
            intervention_amt=Decimal("10.00"),
        )

        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(response.data["interventions"][0]["actual_amount"]),
            Decimal(fr_header_1.actual_amt_local + fr_header_2.actual_amt_local)
        )
        self.assertEqual(
            Decimal(response.data["interventions"][0]["frs_total_frs_amt"]),
            Decimal(fr_header_1.total_amt_local + fr_header_2.total_amt_local)
        )
        self.assertEqual(
            Decimal(response.data["interventions"][0]["frs_total_intervention_amt"]),
            Decimal(fr_header_1.intervention_amt + fr_header_2.intervention_amt)
        )
        self.assertEqual(
            Decimal(response.data["interventions"][0]["frs_total_outstanding_amt"]),
            Decimal(fr_header_1.outstanding_amt_local + fr_header_2.outstanding_amt_local)
        )

    def test_api_partners_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("staff_members", response.data.keys())
        self.assertEqual(len(response.data["staff_members"]), 1)

    def test_api_partners_update(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "alternate_name": "Updated alternate_name",
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Updated", response.data["alternate_name"])
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

    def test_api_partners_update_hidden(self):
        # make some other type to filter against
        self.assertFalse(Activity.objects.exists())
        data = {
            "hidden": True
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:partner-detail', args=[self.partner.pk]),
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["hidden"], False)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )
