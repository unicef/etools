import datetime
import json

from django.test import SimpleTestCase
from django.urls import reverse

from mock import Mock, patch
from rest_framework import status
from rest_framework.exceptions import ErrorDetail

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import (
    Assessment,
    CoreValuesAssessment,
    Intervention,
    PartnerOrganization,
    PartnerPlannedVisits,
    PartnerType,
)
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    AssessmentFactory,
    InterventionFactory,
    PartnerFactory,
    PartnerPlannedVisitsFactory,
    PartnerStaffFactory,
)
from etools.applications.partners.views.partner_organization_v2 import PartnerOrganizationAddView
from etools.applications.t2f.tests.factories import TravelActivityFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory

INSIGHT_PATH = "etools.applications.partners.views.partner_organization_v2.get_data_from_insight"


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    '''Simple test case to verify URL reversal'''

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('partner-assessment', 'assessments/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/partners/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestPartnerOrganizationDetailAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            partner_type=PartnerType.GOVERNMENT,
            cso_type="International",
            hidden=False,
            vendor_number="DDD",
            short_name="Short name",
        )
        agreement = AgreementFactory(
            partner=cls.partner,
            signed_by_unicef_date=datetime.date.today())

        cls.intervention = InterventionFactory(
            agreement=agreement,
            status=Intervention.CLOSED
        )
        cls.file_type = AttachmentFileTypeFactory(
            code="partners_partner_assessment"
        )

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
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            hidden=False,
            vendor_number="XYZ",
            short_name="City Hunter",
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
        cls.user = UserFactory(is_staff=True)
        cls.user.groups.add(GroupFactory())

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
        mock_insight = Mock(return_value=(False, "Insight Failed"))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=123".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "Insight Failed"})

    def test_vendor_exists(self):
        PartnerFactory(vendor_number="321")
        mock_insight = Mock(return_value=(True, {
            "ROWSET": {
                "ROW": {"VENDOR_CODE": "321"}
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
            {"error": "This vendor number already exists in eTools"}
        )

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
                    "TOTAL_CASH_TRANSFERRED_CP": "2,000",
                    "CORE_VALUE_ASSESSMENT_DT": "01-Jan-01",
                    "COUNTRY": "239",
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
        self.assertEqual(partner.partner_type, PartnerType.UN_AGENCY)
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
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            hidden=False,
            vendor_number="DDD",
            short_name="Short name",
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
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.unicef_staff.groups.add(GroupFactory(name='Partnership Manager'))
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
        cls.partner = PartnerFactory(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            hidden=False,
            vendor_number="DDD",
            short_name="Short name",
        )
        cls.partner_staff = PartnerStaffFactory(partner=cls.partner)
        cls.partnership_manager_user = UserFactory(is_staff=True)
        cls.partnership_manager_user.groups.add(GroupFactory())
        cls.partnership_manager_user.profile.partner_staff_member = cls.partner_staff.id
        cls.partnership_manager_user.save()

    def setUp(self):
        self.assessment = AssessmentFactory(
            partner=self.partner,
            completed_date=None,
            report=None,
        )
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
