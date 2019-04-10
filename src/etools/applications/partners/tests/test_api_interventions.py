import datetime
import json
from unittest import skip

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIRequestFactory
from unicef_attachments.models import Attachment
from unicef_locations.tests.factories import LocationFactory
from unicef_snapshot.models import Activity

from etools.applications.attachments.models import AttachmentFlat
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.environment.tests.factories import TenantSwitchFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import Intervention, InterventionAmendment, InterventionResultLink
from etools.applications.partners.permissions import InterventionPermissions
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    FileTypeFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.partners.tests.test_utils import setup_intervention_test_data
from etools.applications.reports.models import AppliedIndicator, ReportingRequirement
from etools.applications.reports.tests.factories import (
    AppliedIndicatorFactory,
    CountryProgrammeFactory,
    IndicatorFactory,
    LowerResultFactory,
    ReportingRequirementFactory,
    ResultFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory
from etools.libraries.djangolib.utils import get_all_field_names


def _add_user_to_partnership_manager_group(user):
    """Utility function to add a user to the 'Partnership Manager' group which may or may not exist"""
    group = GroupFactory(name='Partnership Manager')
    user.groups.add(group)


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('intervention-list', '', {}),
            ('intervention-list-dash', 'dash/', {}),
            ('intervention-detail', '1/', {'pk': 1}),
            ('intervention-attachments-update', 'attachments/1/', {'pk': 1}),
            ('intervention-indicators', 'indicators/', {}),
            ('intervention-results', 'results/', {}),
            ('intervention-amendments', 'amendments/', {}),
            ('intervention-amendments-del', 'amendments/1/', {'pk': 1}),
            ('intervention-map', 'map/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/interventions/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestInterventionsSwagger(BaseTenantTestCase):
    def test_accessing_css_file(self):
        # Because a swagger bug was breaking this (in combination with
        # a particular way we had designed some URLs), this test is to
        # reproduce the problem, then make sure the changes we make fix it.
        # The swagger bug:
        # https://github.com/marcgibbons/django-rest-swagger/issues/702
        # was tickled by our having URLs that end in delete, maybe in
        # combination with having their only method be 'delete'.
        unicef_staff = UserFactory(is_staff=True)
        response = self.forced_auth_req('get', '/api/docs/css/dashboard.css', user=unicef_staff)
        self.assertEqual(200, response.status_code)


class TestInterventionsAPI(BaseTenantTestCase):
    EDITABLE_FIELDS = {
        'draft': ["status", "attachments", "prc_review_document", 'travel_activities',
                  "partner_authorized_officer_signatory", "partner_focal_points", "id",
                  "country_programme", "amendments", "unicef_focal_points", "end", "title",
                  "signed_by_partner_date", "review_date_prc", "frs", "start",
                  "metadata", "submission_date", "agreement", "unicef_signatory_id",
                  "result_links", "contingency_pd", "unicef_signatory", "agreement_id", "signed_by_unicef_date",
                  "partner_authorized_officer_signatory_id", "created", "planned_visits",
                  "planned_budget", "modified", "signed_pd_document", "submission_date_prc", "document_type",
                  "offices", "population_focus", "country_programme_id", "engagement", "sections",
                  "sections_present", "flat_locations", "reporting_periods", "activity",
                  "prc_review_attachment", "signed_pd_attachment", "actionpoint",
                  "reporting_requirements", "special_reporting_requirements", "reference_number_year", "number",
                  "termination_doc_attachment"],
        'signed': [],
        'active': ['']
    }
    REQUIRED_FIELDS = {
        'draft': ['number', 'title', 'agreement', 'document_type', 'reference_number_year'],
        'signed': [],
        'active': ['']
    }
    ALL_FIELDS = get_all_field_names(Intervention) + InterventionPermissions.EXTRA_FIELDS

    def setUp(self):
        setup_intervention_test_data(self)

    def tearDown(self):
        cache.clear()
        if hasattr(self, "ts"):
            self.ts.delete()

    def run_request_list_ep(self, data={}, user=None, method='post'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-list'),
            user=user or self.unicef_staff,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request_attachment_create_ep(self, intervention_pk, data={}, user=None, method='post'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-attachment-list', kwargs={'intervention_pk': intervention_pk}),
            user=user or self.unicef_staff,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request_list_dash_ep(self, data={}, user=None, method='get'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-list-dash'),
            user=user or self.unicef_staff,
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request(self, intervention_id, data=None, method='get', user=None):
        user = user or self.partnership_manager_user
        response = self.forced_auth_req(
            method,
            reverse('partners_api:intervention-detail', kwargs={'pk': intervention_id}),
            user=user,
            data=data or {}
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_api_pd_output_not_populated(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "result_links": [
                {"cp_output": self.result.id,
                 "ll_results": [
                     {"id": None, "name": None, "applied_indicators": []}
                 ]}]
        }
        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention.pk]
            ),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.rendered_content)
        self.assertEqual(result.get('result_links'), {'name': ['This field may not be null.']})
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            0
        )

    def test_dashboard_list_focal_point(self):
        self.active_intervention.unicef_focal_points.add(self.unicef_staff)
        status_code, response = self.run_request_list_dash_ep()
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 1)
        self.draft_intervention = InterventionFactory(agreement=self.agreement,
                                                      status='draft')
        self.draft_intervention.unicef_focal_points.add(self.unicef_staff)
        status_code, response = self.run_request_list_dash_ep()
        self.assertEqual(len(response), 1)

    def test_dashboard_list_partnership_manager(self):
        self.draft_intervention = InterventionFactory(agreement=self.agreement,
                                                      status='draft')
        status_code, response = self.run_request_list_dash_ep(user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 4)

    def test_add_contingency_pd(self):
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention1",
            "contingency_pd": True,
            "agreement": self.agreement.id,
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)

    def add_attachment(self, intervention_id):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        file_type = FileTypeFactory()
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        data = {
            "type": file_type.pk,
            "attachment_document": attachment.pk,
        }
        status_code, response = self.run_request_attachment_create_ep(intervention_id, data, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        attachment.refresh_from_db()
        return attachment

    def test_add_contingency_pd_with_attachment(self):
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention1",
            "contingency_pd": True,
            "agreement": self.agreement.pk,
            "reference_number_year": datetime.date.today().year,

        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_201_CREATED)

        attachment = self.add_attachment(response["id"])

        status_code, response = self.run_request(response["id"], user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)

        attachment_updated = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_updated.file_type.code,
            self.file_type_attachment.code
        )
        self.assertEqual(
            attachment_updated.object_id,
            response["attachments"][0]["id"]
        )
        self.assertEqual(
            attachment_updated.code,
            self.file_type_attachment.code
        )

    def test_add_contingency_pd_with_prc_review_and_signed_pd(self):
        attachment_prc = AttachmentFactory(
            file="test_file_prc.pdf",
            file_type=None,
            code="",
        )
        attachment_pd = AttachmentFactory(
            file="test_file_pd.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment_prc.file_type)
        self.assertIsNone(attachment_prc.content_object)
        self.assertFalse(attachment_prc.code)
        self.assertIsNone(attachment_pd.file_type)
        self.assertIsNone(attachment_pd.content_object)
        self.assertFalse(attachment_pd.code)
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention1",
            "contingency_pd": True,
            "agreement": self.agreement.pk,
            "prc_review_attachment": attachment_prc.pk,
            "signed_pd_attachment": attachment_pd.pk,
            "reference_number_year": datetime.date.today().year
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        attachment_prc_updated = Attachment.objects.get(pk=attachment_prc.pk)
        self.assertEqual(
            attachment_prc_updated.file_type.code,
            self.file_type_prc.code
        )
        self.assertEqual(attachment_prc_updated.object_id, response["id"])
        self.assertEqual(
            attachment_prc_updated.code,
            self.file_type_prc.code
        )
        attachment_pd_updated = Attachment.objects.get(pk=attachment_pd.pk)
        self.assertEqual(
            attachment_pd_updated.file_type.code,
            self.file_type_pd.code
        )
        self.assertEqual(attachment_pd_updated.object_id, response["id"])
        self.assertEqual(
            attachment_pd_updated.code,
            self.file_type_pd.code
        )

    def test_add_one_valid_fr_on_create_pd(self):
        self.assertFalse(Activity.objects.exists())
        frs_data = [self.fr_1.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data,
            "reference_number_year": datetime.date.today().year
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_add_two_valid_frs_on_create_pd(self):
        self.assertFalse(Activity.objects.exists())
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data,
            "reference_number_year": datetime.date.today().year
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_fr_details_is_accurate_on_creation(self):
        self.assertFalse(Activity.objects.exists())
        self.fr_1.vendor_code = self.agreement.partner.vendor_number
        self.fr_2.vendor_code = self.agreement.partner.vendor_number
        self.fr_1.save()
        self.fr_2.save()
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "frs": frs_data,
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertEqual(response['frs_details']['total_actual_amt'],
                         float(sum([self.fr_1.actual_amt_local, self.fr_2.actual_amt_local])))
        self.assertEqual(response['frs_details']['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt_local, self.fr_2.outstanding_amt_local])))
        self.assertEqual(response['frs_details']['total_frs_amt'],
                         float(sum([self.fr_1.total_amt_local, self.fr_2.total_amt_local])))
        self.assertEqual(response['frs_details']['total_intervention_amt'],
                         float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_add_two_valid_frs_on_update_pd(self):
        self.assertFalse(Activity.objects.exists())
        self.fr_1.vendor_code = self.intervention_2.agreement.partner.vendor_number
        self.fr_2.vendor_code = self.intervention_2.agreement.partner.vendor_number
        self.fr_1.save()
        self.fr_2.save()
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertEqual(response['frs_details']['total_actual_amt'],
                         float(sum([self.fr_1.actual_amt_local, self.fr_2.actual_amt_local])))
        self.assertEqual(response['frs_details']['total_outstanding_amt'],
                         float(sum([self.fr_1.outstanding_amt_local, self.fr_2.outstanding_amt_local])))
        self.assertEqual(response['frs_details']['total_frs_amt'],
                         float(sum([self.fr_1.total_amt_local, self.fr_2.total_amt_local])))
        self.assertEqual(response['frs_details']['total_intervention_amt'],
                         float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))
        self.assertTrue(Activity.objects.exists())
        activity = Activity.objects.first()
        self.assertEqual(activity.target, self.intervention_2)
        self.assertEqual(activity.action, Activity.UPDATE)
        self.assertIn("frs", activity.change)
        frs = activity.change["frs"]
        self.assertEqual(frs["before"], [])
        self.assertCountEqual(frs["after"], [self.fr_1.pk, self.fr_2.pk])
        self.assertEqual(activity.by_user, self.partnership_manager_user)

    def test_remove_an_fr_from_pd(self):
        self.assertFalse(Activity.objects.exists())
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

        # Remove fr_1
        frs_data = [self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            2
        )

    def test_fail_add_expired_fr_on_pd(self):
        self.assertFalse(Activity.objects.exists())
        self.fr_1.end_date = timezone.now().date() - datetime.timedelta(days=1)
        self.fr_1.save()

        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch',
                                                 user=self.partnership_manager_user)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertTrue(Activity.objects.exists())

    def test_fail_add_used_fr_on_pd(self):
        self.assertFalse(Activity.objects.exists())
        self.fr_1.intervention = self.intervention
        self.fr_1.save()

        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['frs'],
                         ['One or more of the FRs selected is related '
                          'to a different PD/SSFA, {}'.format(self.fr_1.fr_number)])
        self.assertFalse(Activity.objects.exists())

    def test_add_same_frs_twice_on_pd(self):
        self.assertFalse(Activity.objects.exists())
        frs_data = [self.fr_1.id, self.fr_2.id]
        data = {
            "frs": frs_data
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertTrue(Activity.objects.exists())

        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertCountEqual(response['frs'], frs_data)
        self.assertEqual(Activity.objects.all().count(), 2)

    def test_patch_title_fail_as_unicef_user(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "title": 'Changed Title'
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch',
                                                 user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Activity.objects.exists())

    def test_patch_fails_with_wrong_cp_structure(self):
        self.assertIsNone(self.intervention_2.country_programme)
        self.assertTrue(self.intervention_2.agreement.agreement_type, 'PCA')
        random_cp = CountryProgrammeFactory()
        data = {
            "country_programme": random_cp.id
        }
        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The Country Programme selected on this PD is not the same ', response[0])

    def test_patch_ok_with_wrong_cp_structure(self):
        self.assertIsNone(self.intervention_2.country_programme)
        self.assertTrue(self.intervention_2.agreement.agreement_type, 'PCA')
        data = {
            "country_programme": self.intervention_2.agreement.country_programme.id
        }

        status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_200_OK)

    def test_permissions_for_intervention_status_draft(self):

        # TODO: this tests only with PRP mode on. PRP mode off tests needed here.
        # intervention is in Draft status
        self.assertEqual(self.intervention.status, Intervention.DRAFT)

        # user is UNICEF User
        status_code, response = self.run_request(self.intervention.id, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)

        # all fields are there
        self.assertCountEqual(self.ALL_FIELDS, response['permissions']['edit'].keys())
        edit_permissions = response['permissions']['edit']
        required_permissions = response['permissions']['required']

        self.assertCountEqual(self.EDITABLE_FIELDS['draft'],
                              [perm for perm in edit_permissions if edit_permissions[perm]])
        self.assertCountEqual(self.REQUIRED_FIELDS['draft'],
                              [perm for perm in required_permissions if required_permissions[perm]])

    @skip('add test after permissions file is ready')
    def test_permissions_for_intervention_status_active(self):
        # intervention is in Draft status
        self.assertEqual(self.active_intervention.status, Intervention.ACTIVE)

        # user is UNICEF User
        status_code, response = self.run_request(self.active_intervention.id, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_200_OK)

        # all fields are there
        self.assertCountEqual(self.ALL_FIELDS, response['permissions']['edit'].keys())
        edit_permissions = response['permissions']['edit']
        required_permissions = response['permissions']['required']
        self.assertCountEqual(self.EDITABLE_FIELDS['signed'],
                              [perm for perm in edit_permissions if edit_permissions[perm]])
        self.assertCountEqual(self.REQUIRED_FIELDS['signed'],
                              [perm for perm in required_permissions if required_permissions[perm]])

    def test_list_interventions(self):
        EXPECTED_QUERIES = 9
        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 3)

        section1 = SectionFactory()
        section2 = SectionFactory()

        # add another intervention to make sure that the queries are constant
        data = {
            "document_type": Intervention.PD,
            "title": "My test intervention",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "agreement": self.agreement.id,
            "sections": [section1.id, section2.id],
            "reference_number_year": datetime.date.today().year
        }

        status_code, response = self.run_request_list_ep(data, user=self.partnership_manager_user)
        self.assertEqual(status_code, status.HTTP_201_CREATED)

        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 4)

    def test_list_interventions_w_flag(self):
        self.ts = TenantSwitchFactory(name="prp_mode_off", countries=[connection.tenant])
        self.assertTrue(tenant_switch_is_active(self.ts.name))

        EXPECTED_QUERIES = 9
        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 3)

        section1 = SectionFactory()
        section2 = SectionFactory()

        EXTRA_INTERVENTIONS = 15
        for i in range(0, EXTRA_INTERVENTIONS + 1):
            intervention = InterventionFactory(
                document_type=Intervention.PD,
                start=(timezone.now().date()).isoformat(),
                end=(timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
                agreement=self.agreement,
            )
            intervention.sections.add(section1.pk)
            intervention.sections.add(section2.pk)

        self.assertEqual(Intervention.objects.count(), 4 + EXTRA_INTERVENTIONS)

        with self.assertNumQueries(EXPECTED_QUERIES):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 4 + EXTRA_INTERVENTIONS)


class TestAPIInterventionResultLinkListView(BaseTenantTestCase):
    """Exercise the list view for InterventionResultLinkListCreateView"""
    @classmethod
    def setUpTestData(cls):
        cls.intervention = InterventionFactory()

        cls.result_link1 = InterventionResultLinkFactory(intervention=cls.intervention)
        cls.result_link2 = InterventionResultLinkFactory(intervention=cls.intervention)

        cls.url = reverse('partners_api:intervention-result-links-list',
                          kwargs={'intervention_pk': cls.intervention.id})

        # cls.expected_field_names is the list of field names expected in responses.
        cls.expected_field_names = sorted((
            'cp_output',
            'ram_indicators',
            'cp_output_name',
            'ram_indicator_names',
            'id',
            'intervention',
            'created',
            'modified',
        ))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response, expected_keys=None):
        """Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.expected_field_names. Otherwise, they're compared to whatever is passed in
        expected_keys.
        """
        if expected_keys is None:
            expected_keys = self.expected_field_names

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 2)
        for obj in response_json:
            self.assertIsInstance(obj, dict)
        if expected_keys:
            for d in response_json:
                self.assertEqual(sorted(d.keys()), expected_keys)

        actual_ids = sorted([d.get('id') for d in response_json])
        expected_ids = sorted((self.result_link1.id, self.result_link2.id))

        self.assertEqual(actual_ids, expected_ids)

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok(self):
        """Ensure a staff user has access"""
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission(self):
        """A non-staff user has read access if in the correct group"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkCreateView(BaseTenantTestCase):
    """Exercise the create view for InterventionResultLinkListCreateView"""
    @classmethod
    def setUpTestData(cls):
        cls.intervention = InterventionFactory()

        cls.url = reverse('partners_api:intervention-result-links-list',
                          kwargs={'intervention_pk': cls.intervention.id})

        cp_output = ResultFactory()

        cls.data = {
            'intervention_pk': cls.intervention.id,
            'cp_output': cp_output.id
        }

    def _make_request(self, user):
        return self.forced_auth_req('post', self.url, user=user, data=self.data)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.post(self.url, data=self.data, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        """Ensure group membership is sufficient for create; even non-staff group members can create"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkRetrieveView(BaseTenantTestCase):
    """Exercise the retrieve view for InterventionResultLinkUpdateView"""
    @classmethod
    def setUpTestData(cls):
        cls.intervention_result_link = InterventionResultLinkFactory()

        cls.url = reverse('partners_api:intervention-result-links-update',
                          kwargs={'pk': cls.intervention_result_link.id})

        # cls.expected_keys are the keys expected in a JSON response.
        cls.expected_keys = sorted((
            'cp_output',
            'ram_indicators',
            'cp_output_name',
            'ram_indicator_names',
            'id',
            'intervention',
            'created',
            'modified',
        ))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertEqual(self.expected_keys, sorted(response_json.keys()))

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok(self):
        """Ensure a staff user can access"""
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission_non_staff(self):
        """Ensure group membership is sufficient for retrieval; even non-staff group members can retrieve"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkUpdateView(BaseTenantTestCase):
    """Exercise the update view for InterventionResultLinkUpdateView"""
    @classmethod
    def setUpTestData(cls):
        cls.intervention_result_link = InterventionResultLinkFactory()

        cls.url = reverse('partners_api:intervention-result-links-update',
                          kwargs={'pk': cls.intervention_result_link.id})

        cls.new_cp_output = ResultFactory()

        cls.data = {'cp_output': cls.new_cp_output.id}

    def _make_request(self, user):
        return self.forced_auth_req('patch', self.url, user=user, data=self.data)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        intervention_result_link = InterventionResultLink.objects.get(pk=self.intervention_result_link.id)
        self.assertEqual(intervention_result_link.cp_output.id, self.new_cp_output.id)

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.patch(self.url, data=self.data, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_refused(self):
        """Ensure a staff doesn't have write access"""
        response = self._make_request(UserFactory(is_staff=True))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        """Ensure group membership is sufficient for update; even non-staff group members can update"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionResultLinkDeleteView(BaseTenantTestCase):
    """Exercise the delete view for InterventionResultLinkUpdateView"""
    @classmethod
    def setUpTestData(cls):
        cls.intervention_result_link = InterventionResultLinkFactory()

        cls.url = reverse('partners_api:intervention-result-links-update',
                          kwargs={'pk': cls.intervention_result_link.id})

    def _make_request(self, user):
        return self.forced_auth_req('delete', self.url, user=user)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InterventionResultLink.objects.filter(pk=self.intervention_result_link.id).exists())

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.patch(self.url, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_refused(self):
        """Ensure a staff doesn't have write access"""
        response = self._make_request(UserFactory(is_staff=True))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        """Ensure group membership is sufficient for update; even non-staff group members can update"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionLowerResultListView(BaseTenantTestCase):
    """Exercise the list view for InterventionLowerResultListCreateView"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.result_link = InterventionResultLinkFactory()

        cls.lower_result1 = LowerResultFactory(result_link=cls.result_link)
        cls.lower_result2 = LowerResultFactory(result_link=cls.result_link)

        # Create another result link/lower result pair that will break this test if the views don't filter properly
        LowerResultFactory(result_link=InterventionResultLinkFactory())

        cls.url = reverse('partners_api:intervention-lower-results-list',
                          kwargs={'result_link_pk': cls.result_link.id})

        # cls.expected_field_names is the list of field names expected in responses.
        cls.expected_field_names = sorted(('id', 'code', 'created', 'modified', 'name', 'result_link'))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response, expected_keys=None):
        """Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.expected_field_names. Otherwise, they're compared to whatever is passed in
        expected_keys.
        """
        if expected_keys is None:
            expected_keys = self.expected_field_names

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 2)
        for obj in response_json:
            self.assertIsInstance(obj, dict)
        if expected_keys:
            for d in response_json:
                self.assertEqual(sorted(d.keys()), expected_keys)

        actual_ids = sorted([d.get('id') for d in response_json])
        expected_ids = sorted((self.lower_result1.id, self.lower_result2.id))

        self.assertEqual(actual_ids, expected_ids)

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok(self):
        """Ensure a staff user has access"""
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission(self):
        """A non-staff user has read access if in the correct group"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPIInterventionLowerResultCreateView(BaseTenantTestCase):
    """Exercise the create view for InterventionLowerResultListCreateView"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.result_link = InterventionResultLinkFactory()

        # Create another result link/lower result pair that will break this test if the views don't behave properly
        LowerResultFactory(result_link=InterventionResultLinkFactory())

        cls.url = reverse('partners_api:intervention-lower-results-list',
                          kwargs={'result_link_pk': cls.result_link.id})

        cls.data = {'name': 'my lower result'}

    def _make_request(self, user):
        return self.forced_auth_req('post', self.url, user=user, data=self.data)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())
        # The id of the newly-created lower result should be associated with my result link, and it should be
        # the only one associated with that result link.
        self.assertEqual([response_json['id']],
                         [lower_result.id for lower_result in self.result_link.ll_results.all()])
        self.assertEqual(response_json.get('name'), 'my lower result')

        return response_json

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.post(self.url, data=self.data, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        """Ensure group membership is sufficient for create; even non-staff group members can create"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)

    def test_code_read_only(self):
        """Ensure lower_result.code can't be written"""
        user = UserFactory()
        _add_user_to_partnership_manager_group(user)
        data = self.data.copy()
        data['code'] = 'ZZZ'

        response = self.forced_auth_req('post', self.url, user=user, data=data)
        response_json = self.assertResponseFundamentals(response)

        self.assertNotEqual(response_json.get('code'), 'ZZZ')


class TestAPIInterventionIndicatorsListView(BaseTenantTestCase):
    """Exercise the list view for InterventionIndicatorsListView (these are AppliedIndicator instances)"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.result_link = InterventionResultLinkFactory()

        cls.lower_result = LowerResultFactory(result_link=cls.result_link)

        cls.indicator1 = AppliedIndicatorFactory(lower_result=cls.lower_result)
        cls.indicator2 = AppliedIndicatorFactory(lower_result=cls.lower_result)

        # Create another result link/lower result/indicator combo that will break this test if the views don't
        # filter properly
        AppliedIndicatorFactory(lower_result=LowerResultFactory(result_link=InterventionResultLinkFactory()))

        cls.url = reverse('partners_api:intervention-indicators-list',
                          kwargs={'lower_result_pk': cls.lower_result.id})

        # cls.expected_field_names is the list of field names expected in responses.
        cls.expected_field_names = sorted((
            'id',
            'assumptions',
            'baseline',
            'cluster_indicator_id',
            'cluster_name',
            'cluster_indicator_title',
            'context_code',
            'disaggregation',
            'indicator',
            'locations',
            'lower_result',
            'means_of_verification',
            'section',
            'target',
            'total',
            'created',
            'modified',
            'response_plan_name',
            'is_active',
            'is_high_frequency',
            'measurement_specifications',
            'label',
            'numerator_label',
            'denominator_label'
        ))

    def _make_request(self, user):
        return self.forced_auth_req('get', self.url, user=user)

    def assertResponseFundamentals(self, response, expected_keys=None):
        """Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.expected_field_names. Otherwise, they're compared to whatever is passed in
        expected_keys.
        """
        if expected_keys is None:
            expected_keys = self.expected_field_names

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 2)
        for obj in response_json:
            self.assertIsInstance(obj, dict)
        if expected_keys:
            for d in response_json:
                self.assertEqual(sorted(d.keys()), expected_keys)

        actual_ids = sorted([d.get('id') for d in response_json])
        expected_ids = sorted((self.indicator1.id, self.indicator2.id))

        self.assertEqual(actual_ids, expected_ids)

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok(self):
        """Ensure a staff user has access"""
        response = self._make_request(UserFactory(is_staff=True))
        self.assertResponseFundamentals(response)

    def test_group_permission(self):
        """A non-staff user has read access if in the correct group"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)


class TestAPInterventionIndicatorsCreateView(BaseTenantTestCase):
    """Exercise the create view for InterventionIndicatorsListView (these are AppliedIndicator instances)"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.result_link = InterventionResultLinkFactory()
        cls.lower_result = LowerResultFactory(result_link=cls.result_link)

        # Create another result link/lower result pair that will break this test if the views don't behave properly
        LowerResultFactory(result_link=InterventionResultLinkFactory())

        cls.url = reverse('partners_api:intervention-indicators-list',
                          kwargs={'lower_result_pk': cls.lower_result.id})

        location = LocationFactory()
        section = SectionFactory()

        cls.result_link.intervention.flat_locations.add(location)
        cls.result_link.intervention.sections.add(section)

        cls.data = {'assumptions': 'lorem ipsum',
                    'locations': [location.id],
                    'section': section.id,
                    # indicator (blueprint) is required because the AppliedIndicator model has a unique_together
                    # constraint of (indicator, lower_result).
                    'indicator': {'title': 'my indicator blueprint'},
                    }

    def _make_request(self, user, data=None):
        if data is None:
            data = self.data
        return self.forced_auth_req('post', self.url, user=user, data=data)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())
        # The id of the newly-created indicator should be associated with my lower result, and it should be
        # the only one associated with that result.
        self.assertEqual([response_json['id']],
                         [indicator.id for indicator in self.lower_result.applied_indicators.all()])
        self.assertEqual(response_json.get('assumptions'), 'lorem ipsum')

        return response_json

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.post(self.url, data=self.data, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_non_staff(self):
        """Ensure group membership is sufficient for create; even non-staff group members can create"""
        user = UserFactory()
        response = self._make_request(user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        _add_user_to_partnership_manager_group(user)

        # Now the request should succeed.
        response = self._make_request(user)
        self.assertResponseFundamentals(response)

    def test_multiple_association(self):
        """Ensure a different indicator blueprint can be associated with the same lower_result, but
        the same indicator can't be added twice.
        """
        user = UserFactory()
        _add_user_to_partnership_manager_group(user)
        data = self.data.copy()
        data['indicator'] = {'title': 'another indicator blueprint'}
        response = self._make_request(user, data)
        # OK to add a different indicator
        self.assertResponseFundamentals(response)

        response = self._make_request(user, data)
        # Adding the same indicator again should fail.
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(list(response_json.keys()), ['non_field_errors'])
        self.assertIsInstance(response_json['non_field_errors'], list)
        self.assertEqual(response_json['non_field_errors'],
                         ['This indicator is already being monitored for this Result'])


class TestAPInterventionIndicatorsUpdateView(BaseTenantTestCase):
    """Exercise the update view for InterventionIndicatorsUpdateView
    (these are AppliedIndicator instances)
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.intervention = InterventionFactory()
        cls.result_link = InterventionResultLinkFactory(intervention=cls.intervention)
        cls.lower_result = LowerResultFactory(result_link=cls.result_link)
        # Create another result link/lower result pair that will break this
        # test if the views don't behave properly
        LowerResultFactory(result_link=InterventionResultLinkFactory())
        cls.indicator = AppliedIndicatorFactory(lower_result=cls.lower_result)
        cls.url = reverse(
            'partners_api:intervention-indicators-update',
            args=[cls.indicator.pk]
        )

        location = LocationFactory()
        cls.section = SectionFactory()

        cls.result_link.intervention.flat_locations.add(location)
        cls.result_link.intervention.sections.add(cls.section)
        cls.user = UserFactory()
        _add_user_to_partnership_manager_group(cls.user)

    def setUp(self):
        self.data = {
            "is_active": True,
        }

    def _make_request(self, user, data=None):
        if data is None:
            data = self.data
        return self.forced_auth_req('patch', self.url, user=user, data=data)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())
        # The id of the newly-created indicator should be associated with
        # lower result, and it should be the only one associated with that
        # result.
        self.assertEqual(
            [response_json['id']],
            [indicator.id for indicator in self.lower_result.applied_indicators.all()]
        )
        return response_json

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.patch(self.url, data=self.data, format='json')
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update(self):
        self.data["is_active"] = False
        self.data["is_high_frequency"] = True
        self.assertTrue(self.indicator.is_active)
        self.assertFalse(self.indicator.is_high_frequency)
        self.assertEqual(self.intervention.status, Intervention.DRAFT)
        response = self._make_request(self.user, self.data)
        data = self.assertResponseFundamentals(response)
        self.assertFalse(data["is_active"])
        self.assertTrue(data["is_high_frequency"])
        indicator_updated = AppliedIndicator.objects.get(pk=self.indicator.pk)
        self.assertFalse(indicator_updated.is_active)


class TestInterventionAttachmentDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partnership_manager = UserFactory(is_staff=True)
        cls.partnership_manager.groups.add(GroupFactory())
        cls.intervention = InterventionFactory()
        cls.attachment = InterventionAttachmentFactory(
            intervention=cls.intervention,
            attachment="random_attachment.pdf",
        )
        cls.url = reverse(
            "partners_api:intervention-attachments-update",
            args=[cls.attachment.pk]
        )

    def test_delete(self):
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_invalid(self):
        self.intervention.status = "active"
        self.intervention.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Deleting an attachment can only be done in Draft status"])


class TestInterventionResultListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        InterventionResultLinkFactory()
        cls.intervention = InterventionFactory()
        cls.result = ResultFactory(
            name="Result Name",
            code="Result Code",
        )
        cls.link = InterventionResultLinkFactory(
            intervention=cls.intervention,
            cp_output=cls.result
        )
        cls.url = reverse("partners_api:intervention-results")

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('id', first.keys())
        return response_json, first

    def test_search_empty(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "random"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertFalse(response_json)

    def test_search_number(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:-2]}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)

    def test_search_cp_output_name(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "Name"}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)

    def test_search_cp_output_code(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "Code"}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.link.pk)


class TestInterventionIndicatorListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        InterventionResultLinkFactory()
        cls.intervention = InterventionFactory()
        cls.indicator = IndicatorFactory()
        cls.link = InterventionResultLinkFactory(
            intervention=cls.intervention,
        )
        cls.link.ram_indicators.add(cls.indicator)
        cls.url = reverse("partners_api:intervention-indicators")

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('intervention', first.keys())
        return response_json, first

    def test_search(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:-2]}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["intervention"], self.intervention.pk)

    def test_search_empty(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "random"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertFalse(response_json)


class TestInterventionAmendmentListAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        InterventionAmendmentFactory()
        cls.intervention = InterventionFactory()
        cls.amendment = InterventionAmendmentFactory(
            intervention=cls.intervention,
            amendment_number="321",
        )
        cls.url = reverse("partners_api:intervention-amendments")

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('id', first.keys())
        return response_json, first

    def test_search_intervention_number(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.intervention.number[:-2]}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.amendment.pk)

    @skip("fix count issue")
    def test_search_amendment_number(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": self.amendment.amendment_number}
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.amendment.pk)

    def test_search_empty(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"search": "random"}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertFalse(response_json)


class TestInterventionAmendmentCreateAPIView(BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        self.partnership_manager_user = UserFactory(is_staff=True)
        self.partnership_manager_user.groups.add(GroupFactory())

        self.intervention = InterventionFactory(status=Intervention.SIGNED)
        self.url = reverse(
            "partners_api:intervention-amendments-add",
            kwargs={'intervention_pk': self.intervention.id}
        )

        self.uploaded_file = SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8'))
        self.data = {
            "types": InterventionAmendment.DATES,
            "signed_date": datetime.date.today(),
            "signed_amendment": self.uploaded_file,
        }
        self.file_type_signed_amendment_attachment = AttachmentFileTypeFactory(
            code="partners_intervention_amendment_signed"
        )
        self.file_type_internal_prc_review = AttachmentFileTypeFactory(
            code="partners_intervention_amendment_internal_prc_review"
        )

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json)
        return response_json

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets the 403 smackdown"""
        response = self._make_request(user=UserFactory())
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.post(self.url, data={})
        response = view_info.func(request)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission_partnership_member(self):
        """Ensure group membership is sufficient for create;"""
        user = UserFactory(is_staff=True)
        response = self._make_request(user=user)
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_amendment_invalid_type(self):
        invalid_type = 'invalid_choice'
        response = self._make_request(
            user=self.partnership_manager_user,
            data={"types": [invalid_type], "signed_amendment": self.uploaded_file},
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data['types'],
                          {0: [ErrorDetail(string='"invalid_choice" is not a valid choice.', code=f'{invalid_type}')]})

    def test_create_amendment_other_type_no_description(self):
        response = self._make_request(
            user=self.partnership_manager_user,
            data={
                "types": [InterventionAmendment.OTHER],
                "signed_amendment": self.uploaded_file,
            },
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(
            response.data['non_field_errors'], [ErrorDetail(
                string="Other description required, if type 'Other' selected.",
                code='invalid'
            )]
        )

    def test_create_amendment_invalid_file(self):
        response = self._make_request(
            user=self.partnership_manager_user,
            data={},
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data['signed_amendment'], ['No file was submitted.'])

        response = self._make_request(
            user=self.partnership_manager_user,
            data={'signed_amendment': 'asdf'},
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(
            response.data['signed_amendment'],
            ['The submitted data was not a file. Check the encoding type on the form.']
        )

    def test_create_amendment_invalid_date(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        response = self._make_request(
            user=self.partnership_manager_user,
            data={
                "signed_amendment": self.uploaded_file,
                'signed_date': tomorrow,
                'types': [InterventionAmendment.DATES, ]
            },
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(next(iter(response.data.values())), ['Date cannot be in the future!'])

    def test_create_amendment_success(self):
        response = self._make_request(
            user=self.partnership_manager_user,
            data=self.data,
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        data = self.assertResponseFundamentals(response)
        self.assertEquals(data['intervention'], self.intervention.id)

    def test_create_amendment_with_signed_attachment(self):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        self.data.pop("signed_amendment")
        self.data["signed_amendment_attachment"] = attachment.pk
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        response = self._make_request(
            user=self.partnership_manager_user,
            data=self.data,
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        data = self.assertResponseFundamentals(response)
        self.assertEquals(data['intervention'], self.intervention.pk)
        attachment_updated = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_updated.file_type.code,
            self.file_type_signed_amendment_attachment.code
        )
        self.assertEqual(attachment_updated.object_id, data["id"])
        self.assertEqual(
            attachment_updated.code,
            self.file_type_signed_amendment_attachment.code
        )

    def test_create_amendment_with_internal_prc_review(self):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        flat_qs = AttachmentFlat.objects.filter(attachment=attachment)
        assert flat_qs.exists()
        flat = flat_qs.first()
        assert not flat.partner
        self.data["internal_prc_review"] = attachment.pk
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        response = self._make_request(
            user=self.partnership_manager_user,
            data=self.data,
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        data = self.assertResponseFundamentals(response)
        self.assertEquals(data['intervention'], self.intervention.pk)
        attachment.refresh_from_db()
        self.assertEqual(
            attachment.file_type.code,
            self.file_type_internal_prc_review.code
        )
        self.assertEqual(attachment.object_id, data["id"])
        self.assertEqual(
            attachment.code,
            self.file_type_internal_prc_review.code
        )

        # check denormalization
        flat = flat_qs.first()
        assert flat.partner
        assert flat.pd_ssfa
        assert flat.pd_ssfa_number

    def test_create_amendment_with_internal_prc_review_none(self):
        self.data["internal_prc_review"] = None
        response = self._make_request(
            user=self.partnership_manager_user,
            data=self.data,
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        data = self.assertResponseFundamentals(response)
        self.assertEquals(data['intervention'], self.intervention.pk)

    def test_create_amendment_when_already_in_amendment(self):
        self.intervention.in_amendment = True
        self.intervention.save()

        response = self._make_request(
            user=self.partnership_manager_user,
            data=self.data,
            request_format='multipart',
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(
            next(iter(response.data.values())),
            ['Cannot add a new amendment while another amendment is in progress.']
        )

    def _make_request(self, user=None, data=None, request_format='json', **kwargs):
        return self.forced_auth_req('post', self.url, user=user, data=data, request_format=request_format, **kwargs)


class TestInterventionAmendmentDeleteView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.intervention = InterventionFactory()
        cls.amendment = InterventionAmendmentFactory(
            intervention=cls.intervention,
            types=[InterventionAmendment.RESULTS],
            signed_date=datetime.date.today(),
            signed_amendment="random_amendment.pdf"
        )
        cls.url = reverse(
            "partners_api:intervention-amendments-del",
            args=[cls.amendment.pk]
        )

    def test_delete(self):
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_invalid(self):
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete an amendment"])

    def test_intervention_amendments_delete(self):
        response = self.forced_auth_req(
            'delete',
            reverse("partners_api:intervention-amendments-del", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestInterventionListMapView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("partners_api:intervention-map")
        cls.intervention = InterventionFactory(status=Intervention.DRAFT)

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response."""
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        first = response_json[0]
        self.assertIn('id', first.keys())
        return response_json, first

    def test_get(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.intervention.pk)

    def test_get_param_country_programme(self):
        country_programme = CountryProgrammeFactory()
        agreement = AgreementFactory(country_programme=country_programme)
        intervention = InterventionFactory(agreement=agreement, country_programme=country_programme)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"country_programmes": country_programme.pk},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], intervention.pk)

    def test_get_param_section_with_flag(self):
        section = SectionFactory()
        intervention = InterventionFactory()
        intervention.sections.add(section)

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"sections": section.pk},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], intervention.pk)

    def test_get_param_status(self):
        InterventionFactory(status=Intervention.ACTIVE)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"status": self.intervention.status},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], self.intervention.pk)

    def test_get_param_partner(self):
        partner = PartnerFactory()
        agreement = AgreementFactory(partner=partner)
        intervention = InterventionFactory(agreement=agreement)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"partners": partner.pk},
        )
        data, first = self.assertResponseFundamentals(response)
        self.assertEqual(first["id"], intervention.pk)


class TestInterventionReportingRequirementView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        _add_user_to_partnership_manager_group(cls.unicef_staff)
        cls.intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            status=Intervention.DRAFT,
            in_amendment=True,
        )
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.intervention
        )
        cls.lower_result = LowerResultFactory(result_link=cls.result_link)
        cls.indicator = AppliedIndicatorFactory(lower_result=cls.lower_result)

    def _get_url(self, report_type, intervention=None):
        intervention = self.intervention if intervention is None else intervention
        return reverse(
            "partners_api:intervention-reporting-requirements",
            args=[intervention.pk, report_type]
        )

    def test_get(self):
        for report_type, _ in ReportingRequirement.TYPE_CHOICES:
            report_type = ReportingRequirement.TYPE_QPR
            requirement = ReportingRequirementFactory(
                intervention=self.intervention,
                report_type=report_type
            )
            requirement_qs = ReportingRequirement.objects.filter(
                intervention=self.intervention,
                report_type=report_type
            )
            init_count = requirement_qs.count()
            response = self.forced_auth_req(
                "get",
                self._get_url(report_type),
                user=self.unicef_staff,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                len(response.data["reporting_requirements"]),
                init_count
            )
            requirement_pks = []
            for r in response.data["reporting_requirements"]:
                requirement_pks.append(r["id"])
            self.assertIn(requirement.pk, requirement_pks)
            self.assertEqual(
                len(requirement_pks),
                ReportingRequirement.objects.filter(
                    pk__in=requirement_pks,
                    report_type=report_type
                ).count()
            )

    def test_post_qpr(self):
        report_type = ReportingRequirement.TYPE_QPR
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self._get_url(report_type),
            user=self.unicef_staff,
            data={
                "reporting_requirements": [{
                    "start_date": datetime.date(2001, 1, 1),
                    "end_date": datetime.date(2001, 3, 31),
                    "due_date": datetime.date(2001, 4, 15),
                }, {
                    "start_date": datetime.date(2001, 4, 1),
                    "end_date": datetime.date(2001, 5, 31),
                    "due_date": datetime.date(2001, 5, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(requirement_qs.count(), init_count + 2)
        self.assertEqual(
            len(response.data["reporting_requirements"]),
            init_count + 2
        )

    def test_post_hr(self):
        AppliedIndicatorFactory(
            is_high_frequency=True,
            lower_result=self.lower_result
        )
        report_type = ReportingRequirement.TYPE_HR
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self._get_url(report_type),
            user=self.unicef_staff,
            data={
                "reporting_requirements": [{
                    "start_date": datetime.date(2001, 3, 15),
                    "due_date": datetime.date(2001, 4, 15),
                    "end_date": datetime.date(2001, 4, 15),
                }, {
                    "start_date": datetime.date(2001, 4, 16),
                    "due_date": datetime.date(2001, 5, 15),
                    "end_date": datetime.date(2001, 5, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(requirement_qs.count(), init_count + 2)
        self.assertEqual(
            len(response.data["reporting_requirements"]),
            init_count + 2
        )

    def test_post_invalid_no_report_type(self):
        """Missing report type value"""
        report_type = ReportingRequirement.TYPE_QPR
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self._get_url(report_type),
            user=self.unicef_staff,
            data={
                "reporting_requirements": [{
                    "end_date": datetime.date(2001, 3, 31),
                    "due_date": datetime.date(2001, 4, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(requirement_qs.count(), init_count)
        self.assertEqual(
            response.data,
            {"reporting_requirements": [
                {"start_date": ["This field is required."]}
            ]}
        )

    def test_post_invalid_not_amendment_state(self):
        """Intervention is not in amendment state"""
        intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            status=Intervention.ENDED,
            in_amendment=False,
        )
        result_link = InterventionResultLinkFactory(
            intervention=intervention
        )
        lower_result = LowerResultFactory(result_link=result_link)
        AppliedIndicatorFactory(lower_result=lower_result)

        report_type = ReportingRequirement.TYPE_QPR
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self._get_url(report_type, intervention=intervention),
            user=self.unicef_staff,
            data={
                "report_type": ReportingRequirement.TYPE_HR,
                "reporting_requirements": [{
                    "start_date": datetime.date(2001, 2, 1),
                    "end_date": datetime.date(2001, 3, 31),
                    "due_date": datetime.date(2001, 4, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(requirement_qs.count(), init_count)
        self.assertEqual(
            response.data,
            {"non_field_errors": [
                "Changes not allowed when PD not in amendment state."
            ]}
        )

    def test_requirements_pd_terminated_and_ended_qpr(self):
        intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2002, 1, 1),
            status=Intervention.TERMINATED
        )
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        AppliedIndicatorFactory(lower_result=lower_result)

        response = self.forced_auth_req(
            "post",
            self._get_url(ReportingRequirement.TYPE_QPR, intervention=intervention),
            user=self.unicef_staff,
            data={
                "report_type": ReportingRequirement.TYPE_QPR,
                "reporting_requirements": [{
                    "start_date": datetime.date(2001, 2, 1),
                    "end_date": datetime.date(2001, 3, 31),
                    "due_date": datetime.date(2001, 4, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"non_field_errors": [
                "Changes not allowed when PD is terminated."
            ]}
        )

    def test_requirements_pd_terminated_but_not_ended_qpr(self):
        intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            end=datetime.date.today() + datetime.timedelta(days=2),
            status=Intervention.TERMINATED
        )
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        AppliedIndicatorFactory(lower_result=lower_result)

        response = self.forced_auth_req(
            "post",
            self._get_url(ReportingRequirement.TYPE_QPR, intervention=intervention),
            user=self.unicef_staff,
            data={
                "report_type": ReportingRequirement.TYPE_QPR,
                "reporting_requirements": [{
                    "start_date": datetime.date(2001, 2, 1),
                    "end_date": datetime.date(2001, 3, 31),
                    "due_date": datetime.date(2001, 4, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_requirements_pd_terminated_and_ended_hr(self):
        intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2002, 1, 1),
            status=Intervention.TERMINATED
        )
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        AppliedIndicatorFactory(lower_result=lower_result, is_high_frequency=True)

        response = self.forced_auth_req(
            "post",
            self._get_url(ReportingRequirement.TYPE_HR, intervention=intervention),
            user=self.unicef_staff,
            data={
                "report_type": ReportingRequirement.TYPE_HR,
                "reporting_requirements": [{
                    "start_date": datetime.date(2001, 2, 1),
                    "end_date": datetime.date(2001, 3, 31),
                    "due_date": datetime.date(2001, 4, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"non_field_errors": [
                "Changes not allowed when PD is terminated."
            ]}
        )

    def test_requirements_pd_terminated_but_not_ended_hr(self):
        intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            end=datetime.date.today() + datetime.timedelta(days=2),
            status=Intervention.TERMINATED
        )
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        AppliedIndicatorFactory(lower_result=lower_result, is_high_frequency=True)

        response = self.forced_auth_req(
            "post",
            self._get_url(ReportingRequirement.TYPE_HR, intervention=intervention),
            user=self.unicef_staff,
            data={
                "report_type": ReportingRequirement.TYPE_HR,
                "reporting_requirements": [{
                    "start_date": datetime.date(2001, 2, 1),
                    "end_date": datetime.date(2001, 3, 31),
                    "due_date": datetime.date(2001, 4, 15),
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_invalid(self):
        for report_type, _ in ReportingRequirement.TYPE_CHOICES:
            response = self.forced_auth_req(
                "patch",
                self._get_url(report_type),
                user=self.unicef_staff,
                data={
                    "reporting_requirements": [{
                        "due_date": datetime.date(2001, 4, 15),
                    }]
                }
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED
            )

    def test_delete_invalid_report_type(self):
        for report_type, _ in ReportingRequirement.TYPE_CHOICES:
            response = self.forced_auth_req(
                "delete",
                self._get_url(report_type),
                user=self.unicef_staff,
                data={
                    "reporting_requirements": [{
                        "due_date": datetime.date(2001, 4, 15),
                    }]
                }
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED
            )
