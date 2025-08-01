import csv
import datetime
import json
from unittest import skip
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.http import HttpResponse
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from django.utils import timezone, translation

import mock
from model_utils import Choices
from pytz import UTC
from rest_framework import status
from rest_framework.test import APIRequestFactory
from unicef_locations.tests.factories import LocationFactory
from unicef_snapshot.models import Activity

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.environment.tests.factories import TenantSwitchFactory
from etools.applications.funds.models import FundsCommitmentHeader, FundsCommitmentItem
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import (
    Agreement,
    AgreementAmendment,
    FileType,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionBudget,
    InterventionPlannedVisits,
    InterventionReportingPeriod,
    OrganizationType,
    PartnerOrganization,
)
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, READ_ONLY_API_GROUP_NAME, UNICEF_USER
from etools.applications.partners.serializers.exports.partner_organization import PartnerOrganizationExportSerializer
from etools.applications.partners.tests.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    InterventionFactory,
    InterventionPlannedVisitsFactory,
    InterventionReportingPeriodFactory,
    InterventionResultLinkFactory,
    InterventionSupplyItemFactory,
    PartnerFactory,
    PlannedEngagementFactory,
)
from etools.applications.partners.views import partner_organization_v2, v2
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    ResultFactory,
    ResultTypeFactory,
    SectionFactory,
)
from etools.applications.t2f.models import Travel, TravelType
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('partner-list', '', {}),
            ('partner-engagements', 'engagements/', {}),
            ('partner-detail', '1/', {'pk': 1}),
            ('partner-delete', 'delete/1/', {'pk': 1}),
            ('partner-assessment-detail', 'assessments/1/', {'pk': 1}),
            ('partner-add', 'add/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/partners/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestChoicesToJSONReady(BaseTenantTestCase):
    def test_tuple(self):
        """Make tuple JSON ready"""
        ready = v2.choices_to_json_ready(((1, "One"), (2, "Two")))
        self.assertEqual(ready, [
            {"label": "One", "value": 1},
            {"label": "Two", "value": 2}
        ])

    def test_list(self):
        """Make simple list JSON ready"""
        ready = v2.choices_to_json_ready([1, 2, 3])
        self.assertEqual(ready, [
            {"label": 1, "value": 1},
            {"label": 2, "value": 2},
            {"label": 3, "value": 3},
        ])

    def test_list_of_tuples(self):
        """Make list of tuples JSON ready"""
        ready = v2.choices_to_json_ready([(1, "One"), (2, "Two")])
        self.assertEqual(ready, [
            {"label": "One", "value": 1},
            {"label": "Two", "value": 2}
        ])

    def test_list_of_tuples_sorted(self):
        """Make list of tuples JSON ready"""
        ready = v2.choices_to_json_ready([(1, "Uno"), (2, "Due")])
        self.assertEqual(ready, [
            {"label": "Due", "value": 2},
            {"label": "Uno", "value": 1}
        ])

    def test_dict(self):
        """Make dict JSON ready"""
        ready = v2.choices_to_json_ready({"k": "v"})
        self.assertEqual(ready, [{"label": "v", "value": "k"}])

    def test_dict_sorted(self):
        """Make dict JSON ready"""
        ready = v2.choices_to_json_ready({"k": "v", "a": "b"})
        self.assertEqual(ready, [
            {"label": "b", "value": "a"},
            {"label": "v", "value": "k"}
        ])

    def test_choices(self):
        """Make model_utils.Choices JSON ready"""
        ready = v2.choices_to_json_ready(Choices("one", "two"))
        self.assertEqual(ready, [
            {"label": "one", "value": "one"},
            {"label": "two", "value": "two"},
        ])


class TestAPIPartnerOrganizationListView(BaseTenantTestCase):
    """Exercise the list view for PartnerOrganization"""
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory(is_staff=True)

        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                name='List View Test Partner',
                short_name='List View Test Partner Short Name',
                organization_type=OrganizationType.UN_AGENCY,
                cso_type='International'
            )
        )

        cls.readonly_group = GroupFactory(name=READ_ONLY_API_GROUP_NAME)

        cls.url = reverse('partners_api:partner-list')

    def setUp(self):
        # self.normal_field_names is the list of field names present in responses that don't use an out-of-the-ordinary
        # serializer.
        self.normal_field_names = sorted((
            'address', 'blocked', 'basis_for_risk_rating', 'city', 'country', 'cso_type', 'deleted_flag', 'email',
            'hidden', 'id', 'last_assessment_date', 'name', 'net_ct_cy', 'partner_type', 'phone_number', 'postal_code',
            'rating', 'reported_cy', 'shared_with', 'short_name', 'street_address', 'total_ct_cp', 'total_ct_cy',
            'total_ct_ytd', 'vendor_number', 'psea_assessment_date', 'sea_risk_rating_name',
        ))

    def assertResponseFundamentals(self, response, expected_keys=None):
        """Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.normal_field_names. Otherwise, they're compared to whatever is passed in
        expected_keys.
        """
        if expected_keys is None:
            expected_keys = self.normal_field_names

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        self.assertIsInstance(response_json[0], dict)
        if expected_keys:
            self.assertEqual(sorted(response_json[0].keys()), expected_keys)
        self.assertIn('id', response_json[0].keys())
        self.assertEqual(response_json[0]['id'], self.partner.id)

    def test_simple(self):
        """exercise simple fetch"""
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_no_permission_user_forbidden(self):
        """Ensure a non-staff user gets no data"""
        response = self.forced_auth_req(
            'get',
            self.url,
            user=UserFactory(realms__data=[])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 smackdown"""
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_permission(self):
        """Ensure a non-staff user in the correct group has access"""
        user = UserFactory(realms__data=[self.readonly_group.name])
        response = self.forced_auth_req(
            'get',
            self.url,
            user=user
        )
        self.assertResponseFundamentals(response)

    def test_staff_access(self):
        """Ensure a staff user has access"""
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_verbosity_minimal(self):
        """Exercise behavior when verbosity=minimal"""
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"verbosity": "minimal"},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response, sorted(("id", "name")))

    def test_verbosity_other(self):
        """Exercise behavior when verbosity != minimal. ('minimal' is the only accepted value for verbosity;
        other values are ignored.)
        """
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"verbosity": "banana"},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_filter_partner_type(self):
        """Ensure filtering by partner type works as expected"""
        # Make another partner that should be excluded from the search results.
        PartnerFactory(organization=OrganizationFactory(organization_type=OrganizationType.GOVERNMENT))
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"partner_type": OrganizationType.UN_AGENCY},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_filter_cso_type(self):
        """Ensure filtering by CSO type works as expected"""
        # Make another partner that should be excluded from the search results.
        PartnerFactory(organization=OrganizationFactory(cso_type="National"))
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"cso_type": "International"},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_filter_hidden(self):
        """Ensure filtering by the hidden flag works as expected"""
        # Make another partner that should be excluded from the search results.
        PartnerFactory(hidden=True)
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"hidden": False},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_filter_multiple(self):
        """Test that when supplying multiple filter terms, they're ANDed together"""
        # Make another partner that should be excluded from the search results.
        PartnerFactory(organization=OrganizationFactory(cso_type="National"))
        params = {
            "cso_type": "National",
            "partner_type": OrganizationType.CIVIL_SOCIETY_ORGANIZATION,
        }
        response = self.forced_auth_req(
            'get',
            self.url,
            data=params,
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 0)

    def test_filter_sea_risk_rating(self):
        """Ensure filtering by the sea_risk_rating works as expected"""
        sea_risk_rating = "High"
        self.partner = PartnerFactory(sea_risk_rating_name=sea_risk_rating)
        for _ in range(10):
            PartnerFactory()
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"sea_risk_rating": sea_risk_rating},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_filter_psea_assessment_date_before(self):
        """Ensure filtering by the psea_assessment_date_before works
        as expected"""
        date = datetime.date(2001, 1, 1)
        self.partner = PartnerFactory(psea_assessment_date=date)
        date_after = date + datetime.timedelta(days=20)
        for _ in range(10):
            PartnerFactory(psea_assessment_date=date_after)
        response = self.forced_auth_req(
            'get',
            self.url,
            data={
                "psea_assessment_date_before": date + datetime.timedelta(days=1),
            },
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_filter_psea_assessment_date_after(self):
        """Ensure filtering by the psea_assessment_date_after works
        as expected"""
        date = datetime.date(2001, 1, 1)
        self.partner = PartnerFactory(psea_assessment_date=date)
        date_before = date - datetime.timedelta(days=20)
        for _ in range(10):
            PartnerFactory(psea_assessment_date=date_before)
        response = self.forced_auth_req(
            'get',
            self.url,
            data={
                "psea_assessment_date_after": date - datetime.timedelta(days=1),
            },
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_search_name(self):
        """Test that name search matches substrings and is case-independent"""
        # Make another partner that should be excluded from the search results.
        PartnerFactory(organization=OrganizationFactory(name="Somethingelse"))
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"search": "PARTNER"},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_search_short_name(self):
        """Test that short name search matches substrings and is case-independent"""
        # Make another partner that should be excluded from the search results.
        PartnerFactory(organization=OrganizationFactory(short_name="foo", name='FOO'))
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"search": "SHORT"},
            user=self.unicef_user
        )
        self.assertResponseFundamentals(response)

    def test_values_positive(self):
        """Ensure that passing the values param w/partner ids returns only data for those partners"""
        # In contrast to the other tests, this test uses the two partners I create here and filters out self.partner.
        p1 = PartnerFactory()
        p2 = PartnerFactory()
        # I also pass the id of a non-existent partner to ensure that doesn't make the view choke.
        unused_id = 9999
        while PartnerOrganization.objects.filter(pk=unused_id).exists():
            unused_id += 1

        response = self.forced_auth_req(
            'get',
            self.url,
            data={"values": "{},{},{}".format(p1.id, p2.id, unused_id)},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 2)
        ids_in_response = []
        for list_element in response_json:
            self.assertIsInstance(list_element, dict)
            ids_in_response.append(list_element.get('id'))

        self.assertCountEqual(ids_in_response, (p1.id, p2.id))

    def test_values_negative(self):
        """Ensure that garbage values are handled properly"""
        response = self.forced_auth_req(
            'get',
            self.url,
            data={"values": "banana"},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_switchable_pagination(self):
        [PartnerFactory() for _i in range(15)]
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'page': 1},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 16)


class TestPartnerOrganizationListViewForCSV(BaseTenantTestCase):
    """Exercise the CSV-generating portion of the list view for PartnerOrganization.

    This is a separate test case from TestPartnerOrganizationListView because it does some monkey patching in
    setUp() that I want to do as infrequently as necessary.
    """
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        cls.url = reverse('partners_api:partner-list')

    def setUp(self):
        # Monkey patch the serializer that I expect to be called. I monkey patch with a wrapper that will set a
        # flag here on my test case class before passing control to the normal serializer. I do this so that I can
        # see whether or not the serializer was called. It allows me to perform the equivalent of
        # assertSerializerUsed().
        class Wrapper(PartnerOrganizationExportSerializer):
            def __init__(self, *args, **kwargs):
                TestPartnerOrganizationListViewForCSV.wrapper_called = True
                super().__init__(*args, **kwargs)

        partner_organization_v2.PartnerOrganizationExportSerializer = Wrapper

        TestPartnerOrganizationListViewForCSV.wrapper_called = False

    def tearDown(self):
        # Undo the monkey patch.
        partner_organization_v2.PartnerOrganizationExportSerializer = PartnerOrganizationExportSerializer

    def test_format_csv(self):
        """Exercise the view-specific aspects of passing query param format=csv. This does not test the serializer
        function, it only tests that the expected serializer is invoked and returns something CSV-like.
        """
        self.assertFalse(self.wrapper_called)
        response = self.forced_auth_req('get', self.url, data={"format": "csv"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ensure my wrapper was called, which tells me that the proper serializer was invoked.
        self.assertTrue(self.wrapper_called)

        # The response should be a CSV. I'm explicitly not looking for certain headers (that's for a serializer test)
        # but I want to make sure the response looks CSV-ish.
        self.assertEqual(response.get('Content-Disposition'), 'attachment;filename=partner.csv')

        response_content = response.rendered_content.decode('utf-8')

        self.assertIsInstance(response_content, str)

        # The response should *not* look like JSON.
        with self.assertRaises(ValueError):
            json.loads(response_content)

        lines = response_content.replace('\r\n', '\n').split('\n')
        # Try to read it with Python's CSV reader.
        reader = csv.DictReader(lines)

        # I'm not looking for explicit field names in this test, but it's safe to assume there should be a few.
        self.assertGreaterEqual(len(reader.fieldnames), 5)

        self.assertGreaterEqual(len([row for row in reader]), 1)

    def test_format_other(self):
        """Exercise passing an unrecognized format."""
        # This returns 404, it should probably return 400 but anything in the 4xx series gets the point across.
        response = self.forced_auth_req('get', self.url, data={"format": "banana"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestPartnerOrganizationCreateView(BaseTenantTestCase):
    """Exercise the create view for PartnerOrganization"""
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.url = reverse('partners_api:partner-list')

    def setUp(self):
        self.data = {"name": "PO 1",
                     "partner_type": OrganizationType.GOVERNMENT,
                     "vendor_number": "AAA",
                     "staff_members": [],
                     }

    def assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response. Return the id of the new object."""
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())

        return response_json['id']


class TestPartnershipViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff_member = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.partner.organization,
        )

        agreement = AgreementFactory(partner=cls.partner,
                                     signed_by_unicef_date=datetime.date.today(),
                                     signed_by_partner_date=datetime.date.today(),
                                     signed_by=cls.unicef_staff,
                                     partner_manager=cls.partner_staff_member)
        cls.intervention = InterventionFactory(agreement=agreement)

        cls.result_type = ResultTypeFactory()
        cls.result = ResultFactory(result_type=cls.result_type)
        cls.partnership_budget = cls.intervention.planned_budget
        cls.amendment = InterventionAmendment.objects.create(
            intervention=cls.intervention,
            types=[InterventionAmendment.RESULTS],
        )

    def test_api_partners_list(self):
        response = self.forced_auth_req('get', '/api/v2/partners/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("Partner", response.data[0]["name"])

    def test_api_partners_list_specify_workspace(self):
        # specifying current tenant works
        response = self.forced_auth_req('get', '/api/v2/partners/', user=self.unicef_staff,
                                        data={'workspace': self.tenant.business_area_code})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # specifying invalid tenant fails
        response = self.forced_auth_req('get', '/api/v2/partners/', user=self.unicef_staff,
                                        data={'workspace': ':('})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @skip("different endpoint")
    def test_api_agreements_list(self):

        response = self.forced_auth_req('get', '/api/partners/' + str(self.partner.id) +
                                        '/agreements/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("PCA", response.data[0]["agreement_type"])


class TestAgreementCreateAPIView(BaseTenantTestCase):
    """Exercise the create portion of the API."""
    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory(organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION)
        cls.partner = PartnerFactory(organization=cls.organization)

        cls.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP],
        )
        cls.file_type_agreement = AttachmentFileTypeFactory()

    def test_minimal_create(self):
        """Test passing as few fields as possible to create"""
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner.id,
            "reference_number_year": datetime.date.today().year
        }
        response = self.forced_auth_req(
            'post',
            reverse("partners_api:agreement-list"),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check snapshot creation
        self.assertTrue(Activity.objects.exists())
        activity = Activity.objects.first()
        self.assertEqual(activity.action, Activity.CREATE)
        self.assertEqual(activity.change, {})
        self.assertEqual(activity.by_user, self.partnership_manager_user)

    def test_create_simple_fail(self):
        """Verify that failing gives appropriate feedback"""
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner.id,
            "reference_number_year": datetime.date.today().year
        }
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:agreement-list'),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIsInstance(response.data, dict)
        self.assertEqual(list(response.data.keys()), ['country_programme'])
        self.assertIsInstance(response.data['country_programme'], list)
        self.assertEqual(response.data['country_programme'][0], 'Country Programme is required for PCAs!')

        # Check that no snapshot was created
        self.assertFalse(Activity.objects.exists())


class TestAgreementAPIFileAttachments(BaseTenantTestCase):
    """Test retrieving attachments to agreements and agreement amendments. The file-specific fields are read-only
    on the relevant serializers, so they can't be edited through the API.
    """
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION))
        cls.partnership_manager_user = UserFactory(is_staff=True)
        cls.agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            partner=cls.partner,
            attached_agreement=None,
        )
        cls.file_type_agreement = AttachmentFileTypeFactory()

    def _get_and_assert_response(self):
        """Helper method to get the agreement and verify some basic about the response JSON (which it returns)."""
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-detail', kwargs={'pk': self.agreement.id}),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)

        return response_json

    def test_retrieve_attachment(self):
        """Exercise getting agreement attachment and agreement amendment attachments both when they're present
        and absent.
        """
        # The agreement starts with no attachment.
        response_json = self._get_and_assert_response()
        self.assertIsNone(response_json['attached_agreement_file'])

        # Now add an attachment. Note that in Python 2, the content must be str, in Python 3 the content must be
        # bytes. I think the existing code is compatible with both.
        self.agreement.attached_agreement = SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8'))
        self.agreement.save()

        response_json = self._get_and_assert_response()
        self.assertIn('attached_agreement_file', response_json)

        url = response_json['attached_agreement_file']

        # url is a URL like this one --
        # http://testserver/media/test/file_attachments/partner_organization/934/agreements/PCA2017841/foo.txt

        url = urlparse(url)
        self.assertIn(url.scheme, ('http', 'https'))
        self.assertEqual(url.netloc, 'testserver')

        # The filename is probably 'hello_world.txt', but Django doesn't guarantee that so I don't test it.
        # Joining and splitting on '/' makes sure we get the same results as urlsplit('/') even
        # if any components contain '/'.
        expected_path_components = '/'.join(['',
                                             settings.MEDIA_URL.strip('/'),
                                             connection.schema_name,
                                             'file_attachments',
                                             'partner_organization',
                                             str(self.agreement.partner.id),
                                             'agreements',
                                             # Note that slashes have to be stripped from the agreement number to match the
                                             # normalized path.
                                             self.agreement.agreement_number.strip('/'),
                                             ]).split('/')
        self.assertEqual(expected_path_components, url.path.split('/')[:-1])

        # Confirm that there are no amendments as of yet.
        self.assertIn('amendments', response_json)
        self.assertEqual(response_json['amendments'], [])

        # Now add an amendment.
        amendment = AgreementAmendmentFactory(agreement=self.agreement, signed_amendment=None)
        amendment.signed_amendment = SimpleUploadedFile('goodbye_world.txt', 'goodbye world!'.encode('utf-8'))
        amendment.save()

        response_json = self._get_and_assert_response()
        self.assertIn('amendments', response_json)
        self.assertEqual(len(response_json['amendments']), 1)
        response_amendment = response_json['amendments'][0]

        self.assertIsInstance(response_amendment, dict)

        self.assertIn('signed_amendment_file', response_amendment)

        url = response_amendment['signed_amendment_file']

        # url looks something like this --
        # http://testserver/media/test/file_attachments/partner_org/1658/agreements/MOU20171421/amendments/tmp02/goodbye_world.txt

        url = urlparse(url)
        self.assertIn(url.scheme, ('http', 'https'))
        self.assertEqual(url.netloc, 'testserver')

        # The filename is probably 'goodbye_world.txt', but Django doesn't guarantee that so I don't test it.
        # Joining and splitting on '/' makes sure we get the same results as urlsplit('/') even
        # if any components contain '/'.
        expected_path_components = '/'.join(['',
                                             settings.MEDIA_URL.strip('/'),
                                             connection.schema_name,
                                             'file_attachments',
                                             'partner_org',
                                             str(self.agreement.partner.id),
                                             'agreements',
                                             self.agreement.base_number.strip('/'),
                                             'amendments',
                                             amendment.number.strip('/'),
                                             ]).split('/')
        self.assertEqual(expected_path_components, url.path.split('/')[:-1])


class TestAgreementAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(
            is_staff=True,
            realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        cls.organization = OrganizationFactory(
            name='Partner',
            organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION)
        cls.partner = PartnerFactory(organization=cls.organization)

        cls.partner_staff_user = UserFactory(
            is_staff=True,
            profile__organization=cls.organization,
        )

        cls.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[PARTNERSHIP_MANAGER_GROUP],
            profile__organization=cls.organization
        )
        cls.partner_staff2 = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.organization,
        )

        cls.notify_path = "etools.applications.partners.utils.send_notification_with_template"

        today = datetime.date.today()
        cls.country_programme = CountryProgrammeFactory(
            from_date=datetime.date(today.year - 1, 1, 1),
            to_date=datetime.date(today.year + 1, 1, 1))

        cls.agreement = AgreementFactory(
            partner=cls.partner,
            partner_manager=cls.partner_staff_user,
            country_programme=cls.country_programme,
            start=datetime.date.today(),
            end=cls.country_programme.to_date,
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            signed_by=cls.unicef_staff,
        )
        cls.agreement.authorized_officers.add(cls.partner_staff_user)
        cls.agreement.save()

        cls.amendment1 = AgreementAmendment.objects.create(
            number="001",
            agreement=cls.agreement,
            signed_amendment="application/pdf",
            signed_date=datetime.date.today(),
            types=[AgreementAmendment.IP_NAME]
        )
        cls.amendment2 = AgreementAmendment.objects.create(
            number="002",
            agreement=cls.agreement,
            signed_amendment="application/pdf",
            signed_date=datetime.date.today(),
            types=[AgreementAmendment.BANKING_INFO]
        )
        cls.agreement2 = AgreementFactory(
            partner=cls.partner,
            agreement_type=Agreement.MOU,
            status=Agreement.DRAFT,
        )
        cls.intervention = InterventionFactory(
            agreement=cls.agreement,
            document_type=Intervention.PD)
        cls.file_type_agreement = AttachmentFileTypeFactory()

        cls.fake_insight_data = {
            "ROWSET": {
                "ROW": {
                    "VENDOR_BANK": {
                        "VENDOR_BANK_ROW": {
                            "STREET": "test",
                            "CITY": "test",
                            "ACCT_HOLDER": "test",
                            "BANK_ACCOUNT_CURRENCY": "test",
                            "BANK_NAME": "test",
                            "SWIFT_CODE": "test",
                            "BANK_ACCOUNT_NO": "test",
                            "TAX_NUMBER_5": "test",
                        }
                    }
                }
            }
        }

    def test_cp_end_date_update(self):
        data = {
            'agreement_type': Agreement.PCA,
        }
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.partner_staff_user,
            data=data
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response_json:
            self.assertEqual(r['end'], self.country_programme.to_date.isoformat())

        self.country_programme.to_date = self.country_programme.to_date + datetime.timedelta(days=1)
        self.country_programme.save()
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.partner_staff_user,
            data=data
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response_json:
            self.assertEqual(r['end'], self.country_programme.to_date.isoformat())

    def test_agreements_list(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])

    def test_null_update_generates_no_activity_stream(self):
        """Verify that a do-nothing update doesn't create anything in the model's activity stream"""
        data = {
            "agreement_number": self.agreement.agreement_number
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:agreement-detail', args=[self.agreement.pk]),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agreements_retrieve(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-detail', args=[self.agreement.pk]),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["agreement_number"], self.agreement.agreement_number)

    def test_agreements_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-detail', args=[self.agreement.pk]),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["authorized_officers"][0]["first_name"], self.partner_staff_user.first_name)

    def test_agreements_update_partner_staff(self):
        data = {
            "authorized_officers": [
                self.partner_staff_user.id,
                self.partner_staff2.id
            ],
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:agreement-detail', args=[self.agreement.pk]),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["authorized_officers"]), 2)

        # Check for activity action created
        self.assertTrue(Activity.objects.exists())
        self.assertEqual(
            Activity.objects.filter(action=Activity.UPDATE).count(),
            1
        )

    def test_agreements_delete_fail_wrong_ep(self):
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:agreement-detail', args=[self.agreement.pk]),
            user=self.partnership_manager_user
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_agreements_delete(self):
        new_agreement = AgreementFactory(status=Agreement.DRAFT)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:agreement-delete', args=[new_agreement.pk]),
            user=self.partnership_manager_user
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agreements_list_filter_type(self):
        params = {"agreement_type": Agreement.PCA}
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.agreement.id)
        self.assertEqual(response.data[0]["agreement_type"], Agreement.PCA)

    def test_agreements_list_filter_status(self):
        params = {"status": "signed"}
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.agreement.id)
        self.assertEqual(response.data[0]["status"], Agreement.SIGNED)

    def test_agreements_list_filter_partner_name(self):
        params = {"partner_name": self.partner.name}
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(self.partner.name, response.data[0]["partner_name"])

    def test_agreements_list_filter_special_conditions_pca(self):
        agreement_qs = Agreement.objects.filter(special_conditions_pca=False)
        params = {"special_conditions_pca": "false"}
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), agreement_qs.count())

    def test_agreements_list_filter_search(self):
        params = {"search": "Partner"}
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])

    def test_agreements_list_filter_search_refno(self):
        params = {"search": datetime.date.today().year}
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:agreement-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # self.assertEqual(response.data[1]["agreement_number"], self.agreement.agreement_number)

    def test_agreements_update_set_to_active_on_save(self):
        """Ensure that a draft agreement auto-transitions to signed when saved with signing info"""
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            status=Agreement.DRAFT,
            partner=self.partner,
            partner_manager=self.partner_staff_user,
            start=datetime.date.today(),
            end=self.country_programme.to_date,
            signed_by=self.unicef_staff,
        )
        # In order to auto-transition to signed, this agreement needs authorized officers
        agreement.authorized_officers.add(self.partner_staff_user)
        agreement.save()

        today = datetime.date.today()
        data = {
            "start": today - datetime.timedelta(days=5),
            "end": today + datetime.timedelta(days=5),
            "signed_by_unicef_date": datetime.date.today(),
        }
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                'patch',
                reverse('partners_api:agreement-detail', args=[agreement.pk]),
                user=self.partnership_manager_user,
                data=data
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Agreement.SIGNED)
        mock_send.assert_not_called()

    def test_partner_agreements_update_suspend(self):
        """Ensure that interventions related to an agreement are suspended when the agreement is suspended"""
        # There's a limited number of statuses that the intervention can have in order to transition to suspended;
        # signed is one of them.
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()

        data = {
            "status": Agreement.SUSPENDED,
        }
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                'patch',
                reverse('partners_api:agreement-detail', args=[self.agreement.pk]),
                user=self.partnership_manager_user,
                data=data
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Agreement.SUSPENDED)
        self.assertEqual(Intervention.objects.get(agreement=self.agreement).status, Intervention.SUSPENDED)
        mock_send.assert_called()

    def test_agreement_amendment_delete_error(self):
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners_api:agreement-amendment-del',
                args=[self.agreement.amendments.first().pk]
            ),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete a signed amendment"])

    def test_agreement_generate_pdf_terms_required(self):
        self.client.force_login(self.unicef_staff)
        self.agreement.terms_acknowledged_by = None
        self.agreement.save()
        self.assertEqual(self.agreement.terms_acknowledged_by, None)

        with mock.patch('easy_pdf.views.PDFTemplateView.render_to_response') as render_mock:
            render_mock.return_value = HttpResponse(200)
            with mock.patch('etools.applications.partners.views.v1.get_data_from_insight') as mock_get_insight:
                mock_get_insight.return_value = (True, self.fake_insight_data)
                self.client.get(
                    reverse('partners_api:pca_pdf', args=[self.agreement.pk]),
                    data={}
                )
        render_mock.assert_called()
        context = render_mock.mock_calls[0][1][0]
        self.assertDictEqual(context, {'error': 'Terms to be acknowledged'})
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.terms_acknowledged_by, None)

    def test_agreement_generate_pdf_partnership_manager_required(self):
        self.client.force_login(UserFactory(is_staff=True))
        self.agreement.terms_acknowledged_by = None
        self.agreement.save()
        self.assertEqual(self.agreement.terms_acknowledged_by, None)

        with mock.patch('easy_pdf.views.PDFTemplateView.render_to_response') as render_mock:
            render_mock.return_value = HttpResponse(200)
            with mock.patch('etools.applications.partners.views.v1.get_data_from_insight') as mock_get_insight:
                mock_get_insight.return_value = (True, self.fake_insight_data)
                self.client.get(
                    reverse('partners_api:pca_pdf', args=[self.agreement.pk]),
                    data={'terms_acknowledged': 'true'}
                )
        render_mock.assert_called()
        context = render_mock.mock_calls[0][1][0]
        self.assertDictEqual(context, {'error': 'Partnership Manager role required for pca export.'})
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.terms_acknowledged_by, None)

    def test_agreement_generate_pdf_default(self):
        self.client.force_login(self.unicef_staff)
        self.agreement.terms_acknowledged_by = None
        self.agreement.save()
        self.assertEqual(self.agreement.terms_acknowledged_by, None)

        with mock.patch('etools.applications.partners.views.v1.get_data_from_insight') as mock_get_insight:
            mock_get_insight.return_value = (True, self.fake_insight_data)
            response = self.client.get(
                reverse('partners_api:pca_pdf', args=[self.agreement.pk]),
                data={'terms_acknowledged': 'true'}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.terms_acknowledged_by, self.unicef_staff)

    def test_agreement_generate_pdf_valid(self):
        self.client.force_login(self.unicef_staff)

        with mock.patch('easy_pdf.views.PDFTemplateView.render_to_response') as render_mock:
            render_mock.return_value = HttpResponse(200)
            with mock.patch('etools.applications.partners.views.v1.get_data_from_insight') as mock_get_insight:
                mock_get_insight.return_value = (True, self.fake_insight_data)
                self.client.get(
                    reverse('partners_api:pca_pdf', args=[self.agreement.pk]),
                    data={'terms_acknowledged': 'true'}
                )

        render_mock.assert_called()
        context = render_mock.mock_calls[0][1][0]
        self.assertIsNone(context['error'])
        self.assertEqual(context['pagesize'], 'Letter')

    def test_agreement_generate_pdf_lang(self):
        self.client.force_login(self.unicef_staff)
        params = {
            "lang": "spanish",
            "terms_acknowledged": "true",
        }

        with mock.patch('easy_pdf.views.PDFTemplateView.render_to_response') as render_mock:
            render_mock.return_value = HttpResponse(200)
            with mock.patch('etools.applications.partners.views.v1.get_data_from_insight') as mock_get_insight:
                mock_get_insight.return_value = (True, self.fake_insight_data)
                self.client.get(
                    reverse('partners_api:pca_pdf', args=[self.agreement.pk]),
                    data=params
                )

        render_mock.assert_called()
        context = render_mock.mock_calls[0][1][0]
        self.assertIsNone(context['error'])
        self.assertEqual(context['view'].template_name, 'pca/spanish_pdf.html')

    def test_agreement_add_amendment_type(self):
        amd_types = self.amendment1.types
        amd_types.append(AgreementAmendment.AUTHORIZED_OFFICER)
        data = {
            "amendments": [
                {
                    "id": self.amendment1.id,
                    "types": amd_types
                }
            ]
        }
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:agreement-detail', args=[self.agreement.pk]),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["amendments"][1]["types"]), 2)


class TestInterventionViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        cls.agreement = AgreementFactory()
        cls.agreement2 = AgreementFactory(status="draft")
        cls.partnerstaff = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.agreement.partner.organization,
        )
        cls.planned_engagement = PlannedEngagementFactory(partner=cls.agreement.partner)

    def setUp(self):
        data = {
            "document_type": Intervention.SPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "unicef_budget": 0,
            "agreement": self.agreement.id,
            "reference_number_year": datetime.date.today().year,
            "unicef_focal_points": [self.partnership_manager_user.id]
        }
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-list'),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.intervention = response.data

        self.section = SectionFactory()

        self.fund_commitment_header = FundsCommitmentHeader.objects.create(
            vendor_code="test1",
            fc_number="3454354",
        )

        self.funding_commitment1 = FundsCommitmentItem.objects.create(
            fund_commitment=self.fund_commitment_header,
            line_item="1",
            grant_number="grant 1",
            fr_number="12345",
            wbs="some_wbs",
            fc_ref_number="some_fc_ref",
            commitment_amount=200,
        )

        self.funding_commitment2 = FundsCommitmentItem.objects.create(
            fund_commitment=self.fund_commitment_header,
            line_item="2",
            grant_number="grant 1",
            fr_number="45678",
            wbs="some_wbs",
            fc_ref_number="some_fc_ref",
            commitment_amount=300,
        )

        self.fr_header_1 = FundsReservationHeaderFactory(fr_number=self.funding_commitment1.fr_number)
        self.fr_header_2 = FundsReservationHeaderFactory(fr_number=self.funding_commitment2.fr_number)

        output_type = ResultTypeFactory(name=ResultType.OUTPUT)
        # Basic data to adjust in tests
        self.intervention_data = {
            "agreement": self.agreement2.id,
            "partner_id": self.agreement2.partner.id,
            "document_type": Intervention.SPD,
            "title": "2009 EFY AWP Updated",
            "status": Intervention.DRAFT,
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "submission_date_prc": "2016-10-31",
            "review_date_prc": "2016-10-28",
            "submission_date": "2016-10-28",
            "prc_review_document": None,
            "signed_by_unicef_date": "2016-10-28",
            "signed_by_partner_date": "2016-10-20",
            "unicef_signatory": self.unicef_staff.id,
            "unicef_focal_points": [],
            "partner_focal_points": [],
            "partner_authorized_officer_signatory": self.partnerstaff.id,
            "offices": [],
            "population_focus": "Some focus",
            "planned_visits": [
                {
                    "year": 2016,
                    "programmatic": 2,
                    "spot_checks": 1,
                    "audit": 1,
                    "quarter": 'q1'
                },
            ],
            "sections": [self.section.id],
            "result_links": [
                {
                    "cp_output": ResultFactory(result_type=output_type).id,
                    "ram_indicators": []
                }
            ],
            "amendments": [],
            "attachments": [],
            "reference_number_year": datetime.date.today().year
        }

        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-list'),
            user=self.partnership_manager_user,
            data=self.intervention_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.intervention_data = response.data
        self.intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        self.planned_visit = InterventionPlannedVisits.objects.create(
            intervention=self.intervention_obj
        )
        self.supply_item = InterventionSupplyItemFactory(
            intervention=self.intervention_obj, unit_number=1, unit_price=1
        )
        attachment = "attachment.pdf"
        self.attachment = InterventionAttachment.objects.create(
            intervention=self.intervention_obj,
            attachment=attachment,
            type=FileType.objects.create(name="pdf")
        )
        self.result = InterventionResultLinkFactory(intervention=self.intervention_obj,
                                                    cp_output__result_type=output_type)
        self.amendment = InterventionAmendment.objects.create(
            intervention=self.intervention_obj,
            types=[InterventionAmendment.RESULTS],
        )

        self.intervention_obj.status = Intervention.DRAFT
        self.intervention_obj.save()

    def test_intervention_list(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-list'),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_intervention_list_minimal(self):
        params = {"verbosity": "minimal"}
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(response.data[0].keys()), ["id", "title", "number"])

    def test_intervention_create(self):
        data = {
            "document_type": Intervention.SPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP Updated",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "unicef_budget": 0,
            "agreement": self.agreement.id,
            "reference_number_year": datetime.date.today().year
        }
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-list'),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_intervention_create_unicef_user_fail(self):
        data = {
            "document_type": Intervention.SPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP Updated fail",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "unicef_budget": 0,
            "agreement": self.agreement.id,
            "reference_number_year": datetime.date.today().year
        }
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-list'),
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Accessing this item is not allowed.')

    def test_intervention_retrieve_fr_numbers(self):
        self.fr_header_1.intervention = self.intervention_obj
        self.fr_header_2.intervention = self.intervention_obj
        self.fr_header_1.save()
        self.fr_header_2.save()

        response = self.forced_auth_req(
            'get',
            reverse(
                'partners_api:intervention-detail',
                args=[self.intervention_data.get("id")]
            ),
            user=self.unicef_staff,
        )
        r_data = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r_data["frs_details"]['frs']), 2)
        self.assertCountEqual(r_data["frs"], [self.fr_header_2.id, self.fr_header_1.id])

    def test_intervention_active_update_population_focus(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        self.intervention_data.update(population_focus=None)
        self.intervention_data.update(status="active")
        response = self.forced_auth_req(
            'patch',
            reverse(
                'partners_api:intervention-detail',
                args=[self.intervention_data.get("id")]
            ),
            user=self.partnership_manager_user,
            data=self.intervention_data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @skip('TODO: update test when new validation requirement is built')
    def test_intervention_active_update_planned_budget(self):
        InterventionBudget.objects.filter(intervention=self.intervention_data.get("id")).delete()
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        self.intervention_data.update(status='active')
        self.intervention_data.update(planned_budget=[])
        response = self.forced_auth_req(
            'patch',
            reverse(
                'partners_api:intervention-detail',
                args=[self.intervention_data.get("id")]
            ),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Planned budget is required if Intervention status is ACTIVE or IMPLEMENTED."])

    @skip('Add test back after reintroducing active validations')
    def test_intervention_active_update_planned_budget_rigid(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.ACTIVE
        intervention_obj.save()
        self.intervention_data["planned_budget"][0].update(unicef_cash=0)
        self.intervention_data["planned_budget"][1].update(unicef_cash=0)
        self.intervention_data.update(status="active")

        response = self.forced_auth_req(
            'patch',
            reverse(
                'partners_api:intervention-detail',
                args=[self.intervention_data.get("id")]
            ),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot change fields while intervention is active: unicef_cash"])

    @skip('TODO: update test when new validation requirement is built')
    def test_intervention_active_update_section_locations(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        self.intervention_data.update(sector_locations=[])
        self.intervention_data.update(status="active")
        response = self.forced_auth_req(
            'patch',
            reverse(
                'partners_api:intervention-detail',
                args=[self.intervention_data.get("id")]
            ),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Section locations are required if Intervention status is ACTIVE or IMPLEMENTED."])

    def test_intervention_validation(self):
        response = self.forced_auth_req(
            'post',
            reverse("partners_api:intervention-list"),
            user=self.partnership_manager_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data,
                         {"document_type": ["This field is required."],
                          "agreement": ["This field is required."],
                          "title": ["This field is required."]})

    def test_intervention_delete(self):
        new_intervention = InterventionFactory(status=Intervention.DRAFT)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:intervention-delete', args=[new_intervention.pk]),
            user=self.partnership_manager_user
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_fail_intervention_delete(self):
        new_intervention = InterventionFactory(status=Intervention.ACTIVE)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:intervention-delete', args=[new_intervention.pk]),
            user=self.partnership_manager_user
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_intervention_validation_doctype_pca(self):
        data = {
            "document_type": Intervention.SSFA,
        }
        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention["id"]]
            ),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            '"SSFA" is not a valid choice.',
            response.data["document_type"],
        )

    def test_intervention_validation_doctype_ssfa(self):
        self.agreement.agreement_type = Agreement.SSFA
        self.agreement.save()
        data = {
            "document_type": Intervention.PD,
        }
        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention["id"]]
            ),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Document type PD or HPD can only be associated with a PCA agreement.', response.data)

    def test_intervention_validation_multiple_agreement_ssfa(self):
        self.agreement.agreement_type = Agreement.SSFA
        self.agreement.save()
        intervention = Intervention.objects.get(id=self.intervention["id"])
        intervention.document_type = Intervention.SSFA
        intervention.save()
        self.agreement.interventions.add(intervention)

        response = self.forced_auth_req(
            'post',
            reverse(
                "partners_api:intervention-list"
            ),
            user=self.partnership_manager_user,
            data={
                "agreement": self.agreement.id,
                "document_type": Intervention.SSFA,
                "status": Intervention.DRAFT,
                "title": "test"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You can only add one SSFA Document for each SSFA Agreement', response.data)

    def test_intervention_validation_dates(self):
        today = datetime.date.today()
        data = {
            "start": datetime.date(today.year + 1, 1, 1),
            "end": today,
        }
        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention["id"]]
            ),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['Start date must precede end date'])

    def test_intervention_validation_translation(self):
        today = datetime.date.today()
        data = {
            "start": datetime.date(today.year + 1, 1, 1),
            "end": today,
        }
        with translation.override('fr'):
            response = self.forced_auth_req(
                'patch',
                reverse(
                    "partners_api:intervention-detail",
                    args=[self.intervention["id"]]
                ),
                user=self.partnership_manager_user,
                data=data,
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['La date de début doit précéder la date de fin'])

    def test_intervention_update_planned_visits(self):
        import copy
        a = copy.deepcopy(self.intervention_data["planned_visits"])
        a.append({
            "year": 2015,
            "programmatic": 2,
            "spot_checks": 1,
            "audit": 1,
            "quarter": 'q3'
        })
        data = {
            "planned_visits": a,
        }

        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention["id"]]
            ),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_intervention_update_planned_visits_year_change(self):
        intervention = InterventionFactory()
        intervention.unicef_focal_points.add(self.partnership_manager_user)
        visit = InterventionPlannedVisitsFactory(intervention=intervention)
        visit_qs = InterventionPlannedVisits.objects.filter(
            intervention=intervention,
        )
        self.assertEqual(visit_qs.count(), 1)
        new_year = visit.year + 1
        self.assertNotEqual(visit.year, new_year)
        data = {
            "planned_visits": {
                "id": visit.pk,
                "year": new_year,
                "programmatic": 2,
                "spot_checks": 1,
                "audit": 1,
                "quarter": "q1",
            },
        }

        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[intervention.pk]
            ),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(visit_qs.count(), 1)
        visit.refresh_from_db()
        self.assertEqual(visit.year, new_year)

    def test_intervention_update_planned_visits_fail_due_terminated_status(self):
        self.intervention_obj.status = Intervention.TERMINATED
        self.intervention_obj.save()
        data = {
            "planned_visits": {
                "id": self.intervention_data['planned_visits'][0]['id'],
                "year": 2016,
                "programmatic": 2,
                "spot_checks": 1,
                "audit": 1,
                "quarter": 'q3'
            },
        }

        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention_obj.id]
            ),
            user=self.partnership_manager_user,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['planned_visits'], ['Planned Visit cannot be set for Terminated interventions'])

    def test_intervention_update_planned_visits_fail_due_government_type(self):
        partner = self.intervention_obj.agreement.partner
        partner.organization.organization_type = OrganizationType.GOVERNMENT
        partner.organization.save()

        data = {
            "planned_visits": {
                "id": self.intervention_data['planned_visits'][0]['id'],
                "year": 2016,
                "programmatic": 2,
                "spot_checks": 1,
                "audit": 1,
                "quarter": 'q3'
            },
        }

        response = self.forced_auth_req(
            'patch',
            reverse(
                "partners_api:intervention-detail",
                args=[self.intervention_obj.id]
            ),
            user=self.partnership_manager_user,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['planned_visits'], ['Planned Visit to be set only at Partner level'])

    def test_intervention_delete_planned_visits(self):
        response = self.forced_auth_req(
            'delete',
            reverse(
                "partners_api:interventions-planned-visits-delete",
                args=[self.intervention_obj.id, self.planned_visit.id]
            ),
            user=self.partnership_manager_user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(InterventionPlannedVisits.DoesNotExist):
            self.planned_visit.refresh_from_db()

    def test_intervention_delete_planned_visits_nondraft_fail(self):
        self.intervention_obj.status = Intervention.SIGNED
        self.intervention_obj.save()
        response = self.forced_auth_req(
            'delete',
            reverse(
                "partners_api:interventions-planned-visits-delete",
                args=[self.intervention_obj.id, self.planned_visit.id]
            ),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_intervention_filter(self):
        country_programme = CountryProgrammeFactory()
        office = OfficeFactory()
        user = UserFactory()
        # Test filter
        params = {
            "partnership_type": Intervention.PD,
            "status": Intervention.DRAFT,
            "start": "2016-10-28",
            "end": "2016-10-28",
            "location": "Location",
            "cluster": "Cluster",
            "section": self.section.id,
            "search": "2009",
            "document_type": Intervention.PD,
            "country_programme": country_programme.pk,
            "unicef_focal_points": user.pk,
            "office": office.pk,
            "reference_number_year": datetime.date.today().year
        }
        response = self.forced_auth_req(
            'get',
            reverse("partners_api:intervention-list"),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_intervention_filter_my_partnerships(self):
        # Test filter
        params = {
            "my_partnerships": True,
        }
        response = self.forced_auth_req(
            'get',
            reverse("partners_api:intervention-list"),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_api_interventions_values(self):
        params = {"values": "{}".format(self.intervention["id"])}
        response = self.forced_auth_req(
            'get',
            reverse("partners_api:intervention-list"),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.intervention["id"])

    @skip('fix me')
    def test_intervention_amendment_notificaton(self):
        def _send_req():
            response = self.forced_auth_req(
                'patch',
                reverse('partners_api:intervention-detail', args=[self.intervention_data.get("id")]),
                user=self.partnership_manager_user,
                data=data
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # make sure that the notification template is imported to the DB
        call_command("update_notifications")

        fr = FundsReservationHeaderFactory()
        fr.intervention = self.intervention_obj
        fr.save()

        self.intervention_obj.sections.add(SectionFactory())
        self.intervention_obj.offices.add(OfficeFactory())
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_signed_pd',
            content_object=self.intervention_obj,
        )

        ts = TenantSwitchFactory(name="intervention_amendment_notifications_on", countries=[connection.tenant])
        ts.active = False
        ts.save()

        self.intervention_obj.country_programme = self.intervention_obj.agreement.country_programme
        self.intervention_obj.status = Intervention.ACTIVE
        self.intervention_obj.unicef_focal_points.add(self.unicef_staff)
        self.intervention_obj.partner_focal_points.add(UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.intervention_obj.agreement.partner.organization,
        ))
        self.intervention_obj.budget_owner = UserFactory()
        self.intervention_obj.date_sent_to_partner = datetime.date.today()
        self.intervention_obj.ip_program_contribution = "contribution"
        self.intervention_obj.implementation_strategy = "strategy"
        self.intervention_obj.equity_narrative = "equity narrative"
        self.intervention_obj.context = "context"
        self.intervention_obj.gender_narrative = "gender_narrative"
        self.intervention_obj.save()
        ReportingRequirementFactory(intervention=self.intervention_obj)
        self.assertEqual(self.intervention_obj.status, Intervention.ACTIVE)

        self.assertEqual(self.intervention_obj.in_amendment, True)

        data = {'in_amendment': False}

        mock_send = mock.Mock()
        notifpath = "etools.applications.partners.views.interventions_v2.send_intervention_amendment_added_notification"
        with mock.patch(notifpath, mock_send):
            self.assertFalse(tenant_switch_is_active('intervention_amendment_notifications_on'))
            _send_req()
            self.assertEqual(mock_send.call_count, 0)

        self.intervention_obj.in_amendment = True
        self.intervention_obj.save()

        ts.flush()
        ts.active = True
        ts.save()

        with mock.patch(notifpath, mock_send):
            self.assertTrue(tenant_switch_is_active('intervention_amendment_notifications_on'))
            _send_req()
            self.assertEqual(mock_send.call_count, 1)
            mock_send.assert_called_with(self.intervention_obj)

        self.intervention_obj.refresh_from_db()
        self.assertEqual(self.intervention_obj.in_amendment, False)


class TestInterventionReportingPeriodViews(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        # create a staff user in the Partnership Manager group
        cls.user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        cls.intervention = InterventionFactory()
        cls.list_url = reverse('partners_api:intervention-reporting-periods-list', args=[cls.intervention.pk])
        cls.num_periods = 3
        InterventionReportingPeriodFactory.create_batch(cls.num_periods, intervention=cls.intervention)
        cls.reporting_period = InterventionReportingPeriod.objects.first()
        cls.detail_url = reverse('partners_api:intervention-reporting-periods-detail',
                                 args=[cls.reporting_period.pk])

    def setUp(self):
        self.params = {
            'start_date': datetime.date.today(),
            'end_date': datetime.date.today() + datetime.timedelta(days=1),
            'due_date': datetime.date.today() + datetime.timedelta(days=20),
            'intervention': self.intervention.pk,
        }
        self.one_day = datetime.timedelta(days=1)

    # List

    def test_list(self):
        response = self.forced_auth_req('get', self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(len(data), self.num_periods)
        # check that our keys match our expectation
        self.assertEqual(set(data[0]), {'id', 'start_date', 'end_date', 'due_date', 'intervention'})
        self.assertEqual(data[0]['intervention'], self.intervention.pk)

    def test_list_empty(self):
        InterventionReportingPeriod.objects.all().delete()
        response = self.forced_auth_req('get', self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data, [])

    def test_list_only_our_intervention_periods(self):
        other_intervention = InterventionReportingPeriodFactory()
        response = self.forced_auth_req('get', self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        # only ``num_periods`` items are retrieved ...
        self.assertEqual(len(data), self.num_periods)
        for period in data:
            # ... and other_intervention isn't in there
            self.assertNotEqual(period['intervention'], other_intervention.pk)

    # Create

    def test_create(self):
        # delete existing factory-created objects
        InterventionReportingPeriod.objects.all().delete()
        response = self.forced_auth_req('post', self.list_url, data=self.params)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = json.loads(response.content)
        for key in ['start_date', 'end_date', 'due_date', 'intervention']:
            self.assertEqual(str(data[key]), str(self.params[key]))

    def test_create_required_fields(self):
        params = {}
        response = self.forced_auth_req('post', self.list_url, data=params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        for key in ['start_date', 'end_date', 'due_date', 'intervention']:
            self.assertEqual(data[key], ["This field is required."])

    def test_create_start_must_be_on_or_before_end(self):
        self.params['end_date'] = self.params['start_date'] - self.one_day
        response = self.forced_auth_req('post', self.list_url, data=self.params)
        self.assertContains(response, 'end_date must be on or after start_date',
                            status_code=status.HTTP_400_BAD_REQUEST)

    def test_create_end_must_be_on_or_before_due(self):
        self.params['due_date'] = self.params['end_date'] - self.one_day
        response = self.forced_auth_req('post', self.list_url, data=self.params)
        self.assertContains(response, 'due_date must be on or after end_date',
                            status_code=status.HTTP_400_BAD_REQUEST)

    def test_create_start_must_be_on_or_before_due(self):
        self.params['due_date'] = self.params['start_date'] - self.one_day
        response = self.forced_auth_req('post', self.list_url, data=self.params)
        self.assertContains(response, 'due_date must be on or after end_date',
                            status_code=status.HTTP_400_BAD_REQUEST)

    def set_date_order_and_create(self, old_start_order, old_end_order, new_start_order, new_end_order,
                                  expected_status):
        """
        Helper method to test combinations of start & end date, making sure that
        the view returns the ``expected_status``.
        """
        # delete existing objects which might interfere with this test
        InterventionReportingPeriod.objects.all().delete()
        day_0 = datetime.date.today()
        days = [
            day_0,
            day_0 + 1 * self.one_day,
            day_0 + 2 * self.one_day,
            day_0 + 3 * self.one_day,
        ]
        old_start = days[old_start_order]
        old_end = days[old_end_order]
        new_start = days[new_start_order]
        new_end = days[new_end_order]

        # create the existing instance (old)
        due_date = day_0 + 20 * self.one_day  # <- not important for this test
        InterventionReportingPeriodFactory(
            intervention=self.intervention, due_date=due_date,
            start_date=old_start, end_date=old_end,
        )
        # Now try to create a new instance via the API
        new = self.params.copy()
        new.update({
            'start_date': new_start,
            'end_date': new_end,
        })
        response = self.forced_auth_req('post', self.list_url, data=new)
        self.assertEqual(response.status_code, expected_status)

    def test_create_periods_dont_overlap(self):
        """
        Test various combinations of start and end dates when creating a new
        InterventionReportingPeriod instance. "Old" dates are dates for an
        instance that already exists. "New" dates are dates for an instance
        that we are trying to create.
        """
        # testcases
        # ---------
        # new_start < new_end < old_start < old_end: OK
        # new_start < new_end = old_start < old_end: OK
        # old_start < old_end < new_start < new_end: OK
        # old_start < old_end = new_start < new_end: OK
        # new_start < old_start < new_end < old_end: FAIL
        # new_start < old_start < old_end < new_end: FAIL
        # old_start < new_start < new_end < old_end: FAIL
        # old_start < new_start < old_end < new_end: FAIL
        first, second, third, fourth = range(4)
        OK, FAIL = (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST)

        # arguments: (old_start_order, old_end_order, new_start_order, new_end_order, expected_status)
        self.set_date_order_and_create(third, fourth, first, second, OK)
        self.set_date_order_and_create(third, fourth, first, third, OK)
        self.set_date_order_and_create(first, second, third, fourth, OK)
        self.set_date_order_and_create(first, second, second, fourth, OK)

        self.set_date_order_and_create(second, fourth, first, third, FAIL)
        self.set_date_order_and_create(second, third, first, fourth, FAIL)
        self.set_date_order_and_create(first, fourth, second, third, FAIL)
        self.set_date_order_and_create(first, third, second, fourth, FAIL)

    # Get

    def test_get(self):
        response = self.forced_auth_req('get', self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(set(data.keys()),
                         {'id', 'intervention', 'start_date', 'end_date', 'due_date'})

    def test_get_404(self):
        nonexistent_pk = 0
        url = reverse('partners_api:intervention-reporting-periods-detail',
                      args=[nonexistent_pk])
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Patch

    def test_patch(self):
        params = {
            'due_date': self.reporting_period.due_date + datetime.timedelta(days=1)
        }
        response = self.forced_auth_req('patch', self.detail_url, data=params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['due_date'], str(params['due_date']))

    def test_patch_change_multiple_fields(self):
        params = {
            'end_date': self.reporting_period.end_date + datetime.timedelta(days=1),
            'due_date': self.reporting_period.due_date + datetime.timedelta(days=1),
        }
        response = self.forced_auth_req('patch', self.detail_url, data=params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['end_date'], str(params['end_date']))
        self.assertEqual(data['due_date'], str(params['due_date']))

    def test_patch_order_must_still_be_valid(self):
        params = {
            'end_date': self.reporting_period.start_date - self.one_day
        }
        response = self.forced_auth_req('patch', self.detail_url, data=params)
        self.assertContains(response, 'end_date must be on or after start_date',
                            status_code=status.HTTP_400_BAD_REQUEST)

    def test_patch_cannot_change_intervention(self):
        new_intervention = InterventionFactory()
        params = {
            'intervention': new_intervention.pk
        }
        response = self.forced_auth_req('patch', self.detail_url, data=params)
        self.assertContains(response, 'Cannot change the intervention',
                            status_code=status.HTTP_400_BAD_REQUEST)

    # Delete

    def test_delete(self):
        response = self.forced_auth_req('delete', self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestPartnershipDashboardView(BaseTenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.agreement = AgreementFactory()
        self.agreement2 = AgreementFactory(status=Agreement.DRAFT)
        self.partnerstaff = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.agreement.partner.organization
        )
        data = {
            "document_type": Intervention.SPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP",
            "start": "2016-10-28",
            "end": "2016-10-28",
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            reverse("partners_api:intervention-list"),
            user=self.unicef_staff,
            data=data
        )
        self.intervention = response.data

        self.section = SectionFactory()

        # Basic data to adjust in tests
        self.intervention_data = {
            "agreement": self.agreement2.id,
            "partner_id": self.agreement2.partner.id,
            "document_type": Intervention.SPD,
            "title": "2009 EFY AWP Updated",
            "status": Intervention.DRAFT,
            "start": "2017-01-28",
            "end": "2019-01-28",
            "submission_date_prc": "2017-01-31",
            "review_date_prc": "2017-01-28",
            "submission_date": "2017-01-28",
            "prc_review_document": None,
            "prc_review_attachment": None,
            "signed_by_unicef_date": "2017-01-28",
            "signed_by_partner_date": "2017-01-20",
            "unicef_signatory": self.unicef_staff.id,
            "unicef_focal_points": [],
            "partner_focal_points": [],
            "partner_authorized_officer_signatory": self.partnerstaff.id,
            "offices": [],
            "fr_numbers": None,
            "population_focus": "Some focus",
            "sections": [self.section.id],
            "result_links": [
                {
                    "cp_output": ResultFactory().id,
                    "ram_indicators": []
                },
            ],
            "amendments": [],
            "attachments": [],
        }
        response = self.forced_auth_req(
            'post',
            reverse("partners_api:intervention-list"),
            user=self.unicef_staff,
            data=self.intervention_data
        )
        self.intervention_data = response.data


class TestPartnerOrganizationDashboardAPIView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')
        cls.sec1, cls.sec2, _ = SectionFactory.create_batch(3)
        cls.loc1, cls.loc2, _ = LocationFactory.create_batch(3)
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                organization_type=OrganizationType.UN_AGENCY,
                name="New",
                vendor_number='007'),
            total_ct_cy=1000.00,
            total_ct_cp=789.00,
            total_ct_ytd=123.00,
            outstanding_dct_amount_6_to_9_months_usd=69,
            outstanding_dct_amount_more_than_9_months_usd=90,
            core_values_assessment_date=datetime.date.today() - datetime.timedelta(30),
        )

        cls.unicef_staff = UserFactory(is_staff=True)
        today = datetime.date.today()
        date_200 = datetime.datetime.now() - datetime.timedelta(200)
        date_200 = datetime.datetime(date_200.year, date_200.month, date_200.day, tzinfo=UTC)
        agreement = AgreementFactory(partner=cls.partner, signed_by_unicef_date=today)
        travel = TravelFactory(status=Travel.COMPLETED, traveler=cls.unicef_staff)
        ta = TravelActivityFactory(travel_type=TravelType.PROGRAMME_MONITORING,
                                   date=date_200,
                                   travels=[travel, ], primary_traveler=cls.unicef_staff)
        cls.intervention = InterventionFactory(agreement=agreement, status=Intervention.ACTIVE)
        cls.intervention.sections.set([cls.sec1, cls.sec2])
        cls.intervention.flat_locations.set([cls.loc1, cls.loc2])
        cls.intervention.travel_activities.set([ta, ])
        cls.intervention.save()
        cls.act = ActionPointFactory.create_batch(3, travel_activity=ta, intervention=cls.intervention,
                                                  status=ActionPoint.STATUS_OPEN)

        ActionPointFactory.create_batch(3, intervention=cls.intervention, status=ActionPoint.STATUS_OPEN)
        par = PartnerFactory(organization=OrganizationFactory(name="Other", vendor_number='008'), total_ct_cy=1000.00)
        int = InterventionFactory(agreement=AgreementFactory(partner=par, signed_by_unicef_date=today))
        ActionPointFactory.create_batch(3, travel_activity=ta, intervention=int, status=ActionPoint.STATUS_OPEN)
        call_command('update_notifications')

    def setUp(self):
        self.response = self.forced_auth_req('get', reverse("partners_api:partner-dashboard"), user=self.unicef_staff)
        data = self.response.data
        self.assertEqual(len(data), 1)
        self.record = data[0]

    def test_queryset(self):
        self.assertEqual(self.record['total_ct_cp'], 789.0)
        self.assertEqual(self.record['total_ct_ytd'], 123.0)
        self.assertEqual(self.record['outstanding_dct_amount_6_to_9_months_usd'], 69.00)
        self.assertEqual(self.record['outstanding_dct_amount_more_than_9_months_usd'], 90.00)
        self.assertEqual(self.record['core_value_assessment_expiring'].split()[0], '30')

    def test_sections(self):
        self.assertEqual(self.record['sections'], '{}|{}'.format(self.sec1.name, self.sec2.name))

    def test_locations(self):
        self.assertEqual(self.record['locations'], '{}|{}'.format(self.loc1.name, self.loc2.name))

    def test_action_points(self):
        self.assertEqual(self.record['action_points'], 6)

    def test_no_recent_programmatic_visit(self):
        self.assertEqual(self.record['last_pv_date'], datetime.date.today() - datetime.timedelta(200))
        self.assertEqual(self.record['days_last_pv'], 200)
        self.assertTrue(self.record['alert_no_recent_pv'])
        self.assertFalse(self.record['alert_no_pv'])
        self.assertTrue(self.record['vendor_number'])

    def test_filter_partner_type(self):
        partner_count = PartnerOrganization.objects.filter(
            partner_type=OrganizationType.UN_AGENCY
        ).count()
        response = self.forced_auth_req(
            'get',
            reverse("partners_api:partner-dashboard"),
            data={"partner_type": OrganizationType.UN_AGENCY},
            user=self.unicef_staff
        )
        data = response.data
        self.assertEqual(len(data), partner_count)

    def test_filter_partner_type_none_found(self):
        self.assertEqual(PartnerOrganization.objects.filter(
            partner_type=OrganizationType.GOVERNMENT
        ).count(), 0)
        response = self.forced_auth_req(
            'get',
            reverse("partners_api:partner-dashboard"),
            data={"partner_type": OrganizationType.GOVERNMENT},
            user=self.unicef_staff
        )
        data = response.data
        self.assertEqual(len(data), 0)
