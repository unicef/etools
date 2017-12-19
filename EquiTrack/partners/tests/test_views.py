from __future__ import unicode_literals

import csv
import datetime
from datetime import date, timedelta
from decimal import Decimal
import json
from unittest import skip, TestCase
from urlparse import urlparse

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.db import connection
from django.utils import timezone

from actstream.models import model_stream
from rest_framework import status

from EquiTrack.factories import (
    AgreementAmendmentFactory,
    PartnerFactory,
    UserFactory,
    ResultFactory,
    LocationFactory,
    AgreementFactory,
    PartnerStaffFactory,
    CountryProgrammeFactory,
    GroupFactory,
    InterventionFactory,
    GovernmentInterventionFactory,
    FundsReservationHeaderFactory)
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin
from reports.models import ResultType, Sector
from funds.models import FundsCommitmentItem, FundsCommitmentHeader
from partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    GovernmentInterventionResult,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionBudget,
    InterventionPlannedVisits,
    InterventionResultLink,
    InterventionSectorLocationLink,
    FileType,
    PartnerOrganization,
    PartnerType,
)
from partners.serializers.partner_organization_v2 import PartnerOrganizationExportSerializer
import partners.views.partner_organization_v2


class URLsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('partner-list', '', {}),
            ('partner-hact', 'hact/', {}),
            ('partner-detail', '1/', {'pk': 1}),
            ('partner-delete', 'delete/1/', {'pk': 1}),
            ('partner-assessment-del', 'assessments/1/', {'pk': 1}),
            ('partner-add', 'add/', {}),
            ('partner-staff-members-list', '1/staff-members/', {'partner_pk': 1}),
            )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/partners/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestPartnerOrganizationListView(APITenantTestCase):
    '''Exercise the list view for PartnerOrganization'''
    def setUp(self):
        self.user = UserFactory(is_staff=True)

        self.partner = PartnerFactory(
            name='List View Test Partner',
            short_name='List View Test Partner Short Name',
            partner_type=PartnerType.UN_AGENCY,
            cso_type='International',
        )

        self.url = reverse('partners_api:partner-list')

        # self.normal_field_names is the list of field names present in responses that don't use an out-of-the-ordinary
        # serializer.
        self.normal_field_names = sorted(
            ('blocked', 'cso_type', 'deleted_flag', 'email', 'hidden', 'id', 'name',
             'partner_type', 'phone_number', 'rating', 'shared_partner', 'shared_with',
             'short_name', 'total_ct_cp', 'total_ct_cy', 'vendor_number', )
             )

    def assertResponseFundamentals(self, response, expected_keys=None):
        '''Assert common fundamentals about the response. If expected_keys is None (the default), the keys in the
        response dict are compared to self.normal_field_names. Otherwise, they're compared to whatever is passed in
        expected_keys.
        '''
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
        '''exercise simple fetch'''
        response = self.forced_auth_req('get', self.url)
        self.assertResponseFundamentals(response)

    def test_verbosity_minimal(self):
        '''Exercise behavior when verbosity=minimal'''
        response = self.forced_auth_req('get', self.url, data={"verbosity": "minimal"})
        self.assertResponseFundamentals(response, sorted(("id", "name")))

    def test_verbosity_other(self):
        '''Exercise behavior when verbosity != minimal. ('minimal' is the only accepted value for verbosity;
        other values are ignored.)
        '''
        response = self.forced_auth_req('get', self.url, data={"verbosity": "banana"})
        self.assertResponseFundamentals(response)

    def test_filter_partner_type(self):
        '''Ensure filtering by partner type works as expected'''
        # Make another partner that should be excluded from the search results.
        PartnerFactory(partner_type=PartnerType.GOVERNMENT)
        response = self.forced_auth_req('get', self.url, data={"partner_type": PartnerType.UN_AGENCY})
        self.assertResponseFundamentals(response)

    def test_filter_cso_type(self):
        '''Ensure filtering by CSO type works as expected'''
        # Make another partner that should be excluded from the search results.
        PartnerFactory(cso_type="National")
        response = self.forced_auth_req('get', self.url, data={"cso_type": "International"})
        self.assertResponseFundamentals(response)

    def test_filter_hidden(self):
        '''Ensure filtering by the hidden flag works as expected'''
        # Make another partner that should be excluded from the search results.
        PartnerFactory(hidden=True)
        response = self.forced_auth_req('get', self.url, data={"hidden": False})
        self.assertResponseFundamentals(response)

    def test_filter_multiple(self):
        '''Test that when supplying multiple filter terms, they're ANDed together'''
        # Make another partner that should be excluded from the search results.
        PartnerFactory(cso_type="National")
        params = {
            "cso_type": "National",
            "partner_type": PartnerType.CIVIL_SOCIETY_ORGANIZATION,
        }
        response = self.forced_auth_req('get', self.url, data=params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 0)

    def test_search_name(self):
        '''Test that name search matches substrings and is case-independent'''
        # Make another partner that should be excluded from the search results.
        PartnerFactory(name="Somethingelse")
        response = self.forced_auth_req('get', self.url, data={"search": "PARTNER"})
        self.assertResponseFundamentals(response)

    def test_search_short_name(self):
        '''Test that short name search matches substrings and is case-independent'''
        # Make another partner that should be excluded from the search results.
        PartnerFactory(short_name="foo")
        response = self.forced_auth_req('get', self.url, data={"search": "SHORT"})
        self.assertResponseFundamentals(response)

    def test_values_positive(self):
        '''Ensure that passing the values param w/partner ids returns only data for those partners'''
        # In contrast to the other tests, this test uses the two partners I create here and filters out self.partner.
        p1 = PartnerFactory()
        p2 = PartnerFactory()
        # I also pass the id of a non-existent partner to ensure that doesn't make the view choke.
        unused_id = 9999
        while PartnerOrganization.objects.filter(pk=unused_id).exists():
            unused_id += 1

        response = self.forced_auth_req('get', self.url, data={"values": "{},{},{}".format(p1.id, p2.id, unused_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 2)
        ids_in_response = []
        for list_element in response_json:
            self.assertIsInstance(list_element, dict)
            ids_in_response.append(list_element.get('id'))

        self.assertItemsEqual(ids_in_response, (p1.id, p2.id))

    def test_values_negative(self):
        '''Ensure that garbage values are handled properly'''
        response = self.forced_auth_req('get', self.url, data={"values": "banana"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestPartnerOrganizationListViewForCSV(APITenantTestCase):
    '''Exercise the CSV-generating portion of the list view for PartnerOrganization.

    This is a separate test case from TestPartnerOrganizationListView because it does some monkey patching in
    setUp() that I want to do as infrequently as necessary.
    '''
    def setUp(self):
        # Monkey patch the serializer that I expect to be called with a wrapper that will set a flag here on
        # my test case class before passing control to the normal serializer.
        class Wrapper(PartnerOrganizationExportSerializer):
            def __init__(self, *args, **kwargs):
                TestPartnerOrganizationListViewForCSV.wrapper_called = True
                super(PartnerOrganizationExportSerializer, self).__init__(*args, **kwargs)

        partners.views.partner_organization_v2.PartnerOrganizationExportSerializer = Wrapper

        TestPartnerOrganizationListViewForCSV.wrapper_called = False

        self.user = UserFactory(is_staff=True)
        self.partner = PartnerFactory()
        self.url = reverse('partners_api:partner-list')

    def tearDown(self):
        # Undo the monkey patch.
        partners.views.partner_organization_v2.PartnerOrganizationExportSerializer = PartnerOrganizationExportSerializer

    def test_format_csv(self):
        '''Exercise the view-specific aspects of passing query param format=csv. This does not test the serializer
        function, it only tests that the expected serializer is invoked and returns something CSV-like.
        '''
        self.assertFalse(self.wrapper_called)
        response = self.forced_auth_req('get', self.url, data={"format": "csv"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ensure my wrapper was called, which tells me that the proper serializer was invoked.
        self.assertTrue(self.wrapper_called)

        # The response should be a CSV. I'm explicitly not looking for certain headers (that's for a serializer test)
        # but I want to make sure the response looks CSV-ish.
        self.assertEqual(response.get('Content-Disposition'), 'attachment;filename=partner.csv')

        self.assertIsInstance(response.rendered_content, basestring)

        # The response should *not* look like JSON.
        with self.assertRaises(ValueError):
            json.loads(response.rendered_content)

        lines = response.rendered_content.replace('\r\n', '\n').split('\n')
        # Try to read it with Python's CSV reader.
        reader = csv.DictReader(lines)

        # I'm not looking for explicit field names in this test, but it's safe to assume there should be a few.
        self.assertGreaterEqual(len(reader.fieldnames), 5)

        self.assertGreaterEqual(len([row for row in reader]), 1)

    def test_format_other(self):
        '''Exercise passing an unrecognized format.'''
        # This returns 404, it should probably return 400 but anything in the 4xx series gets the point across.
        response = self.forced_auth_req('get', self.url, data={"format": "banana"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestPartnerOrganizationCreateView(APITenantTestCase):
    '''Exercise the create view for PartnerOrganization'''
    def setUp(self):
        self.user = UserFactory(is_staff=True)
        self.url = reverse('partners_api:partner-list')

    def assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response. Return the id of the new object.'''
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertIn('id', response_json.keys())

        return response_json['id']

    def test_create_simple(self):
        '''Exercise simple create'''
        data = {
            "name": "PO 1",
            "partner_type": PartnerType.GOVERNMENT,
            "vendor_number": "AAA",
            "staff_members": [],
        }
        response = self.forced_auth_req('post', self.url, data=data)
        self.assertResponseFundamentals(response)

    def test_create_with_staff_members(self):
        '''Exercise create with staff members'''
        staff_members = [{
            "title": "Some title",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "a@example.com",
            "active": True,
        }]
        data = {
            "name": "PO 1",
            "partner_type": PartnerType.GOVERNMENT,
            "vendor_number": "AAA",
            "staff_members": staff_members,
        }
        response = self.forced_auth_req('post', self.url, data=data)
        new_id = self.assertResponseFundamentals(response)
        partner = PartnerOrganization.objects.get(pk=new_id)
        staff_members = partner.staff_members.all()
        self.assertEqual(len(staff_members), 1)
        self.assertEqual(staff_members[0].email, 'a@example.com')


class TestPartnerOrganizationRetrieveUpdateDeleteViews(APITenantTestCase):
    '''Exercise the retrieve, update, and delete views for PartnerOrganization'''
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            hidden=False,
            vendor_number="DDD",
            short_name="Short name",
        )

        report = "report.pdf"
        self.assessment1 = Assessment.objects.create(
            partner=self.partner,
            type="Micro Assessment"
        )
        self.assessment2 = Assessment.objects.create(
            partner=self.partner,
            type="Micro Assessment",
            report=report,
            completed_date=datetime.date.today()
        )

        self.partner_gov = PartnerFactory(partner_type=PartnerType.GOVERNMENT)

        agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today())

        self.intervention = InterventionFactory(agreement=agreement)
        self.output_res_type, _ = ResultType.objects.get_or_create(name='Output')

        self.result = ResultFactory(
            result_type=self.output_res_type,)
        self.pcasector = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 1")
        )
        self.partnership_budget = InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.amendment = InterventionAmendment.objects.create(
            intervention=self.intervention,
            types=[InterventionAmendment.RESULTS]
        )
        self.location = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 2")
        )
        self.cp = CountryProgrammeFactory(__sequence=10)
        self.cp_output = ResultFactory(result_type=self.output_res_type)
        self.govint = GovernmentInterventionFactory(
            partner=self.partner_gov,
            country_programme=self.cp
        )
        self.result = ResultFactory()
        self.govint_result = GovernmentInterventionResult.objects.create(
            intervention=self.govint,
            result=self.result,
            year=datetime.date.today().year,
            planned_amount=100,
        )

    def test_api_partners_delete_asssessment_valid(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/partners/assessments/{}/'.format(self.assessment1.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_api_partners_delete_asssessment_error(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/partners/assessments/{}/'.format(self.assessment2.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete a completed assessment"])

    def test_api_partners_update_with_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 1)
        self.assertEqual(response.data["staff_members"][0]["first_name"], "Mace")

        staff_members = [{
            "title": "Some title",
            "first_name": "John",
            "last_name": "Doe",
            "email": "a@a.com",
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
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 2)

    def test_api_partners_update_assessments_invalid(self):
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
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"assessments":
                                         {"completed_date": ["The Date of Report cannot be in the future"]}})

    def test_api_partners_update_assessments_longago(self):
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
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_partners_update_assessments_today(self):
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
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_partners_update_assessments_yesterday(self):
        completed_date = datetime.date.today() - timedelta(days=1)
        assessments = [{
                "id": self.assessment2.id,
                "completed_date": completed_date,
            }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_partners_update_with_members_null_phone(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
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
            "phone": None
        }]
        data = {
            "staff_members": staff_members,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["staff_members"][1]["phone"], None)

    def test_api_partners_update_assessments_tomorrow(self):
        completed_date = datetime.date.today() + timedelta(days=1)
        assessments = [{
                "id": self.assessment2.id,
                "completed_date": completed_date,
            }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"assessments":
                                         {"completed_date": ["The Date of Report cannot be in the future"]}})

    def test_api_partners_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("vendor_number", response.data.keys())
        self.assertIn("address", response.data.keys())
        self.assertIn("Partner", response.data["name"])
        self.assertEqual(['programme_visits', 'spot_checks'], response.data["hact_min_requirements"].keys())
        self.assertEqual(['audits', 'planned_visits', 'spot_checks', 'programmatic_visits'],
                         response.data["hact_values"].keys())
        self.assertEqual(response.data['interventions'], [])

    def test_api_partners_retreive_actual_fr_amounts(self):
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        fr_header_1 = FundsReservationHeaderFactory(intervention=self.intervention)
        fr_header_2 = FundsReservationHeaderFactory(intervention=self.intervention)

        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["interventions"][0]["actual_amount"]),
                         Decimal(fr_header_1.actual_amt + fr_header_2.actual_amt))

    def test_api_partners_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("staff_members", response.data.keys())
        self.assertEqual(len(response.data["staff_members"]), 1)

    def test_api_partners_update(self):
        data = {
            "name": "Updated name again",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Updated", response.data["name"])

    def test_api_partners_delete_with_signed_agreements(self):

        # create draft agreement with partner
        AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            attached_agreement=None,
            status='draft')

        # should have 1 signed and 1 draft agreement with self.partner
        self.assertEqual(self.partner.agreements.count(), 2)

        response = self.forced_auth_req(
            'delete',
            '/api/v2/partners/delete/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], "There was a PCA/SSFA signed with this partner or a transaction "
                                           "was performed against this partner. The Partner record cannot be deleted")

    def test_api_partners_delete_with_draft_agreements(self):
        partner = PartnerFactory(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            hidden=False,
            vendor_number="EEE",
            short_name="Shorter name",
        )

        # create draft agreement with partner
        AgreementFactory(
            partner=partner,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            attached_agreement=None,
            status='draft')

        self.assertEqual(partner.agreements.count(), 1)

        response = self.forced_auth_req(
            'delete',
            '/api/v2/partners/delete/{}/'.format(partner.id),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_api_partners_delete(self):
        partner = PartnerFactory()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/partners/delete/{}/'.format(partner.id),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_api_partners_update_hidden(self):
        # make some other type to filter against
        data = {
            "hidden": True
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["hidden"], False)


class TestPartnershipViews(APITenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory()
        self.partner_staff_member = PartnerStaffFactory(partner=self.partner)

        agreement = AgreementFactory(partner=self.partner,
                                     signed_by_unicef_date=datetime.date.today(),
                                     signed_by_partner_date=datetime.date.today(),
                                     signed_by=self.unicef_staff,
                                     partner_manager=self.partner_staff_member)
        self.intervention = InterventionFactory(agreement=agreement)

        self.result_type = ResultType.objects.get(id=1)
        self.result = ResultFactory(result_type=self.result_type,)
        self.pcasector = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 1")
        )
        self.partnership_budget = InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.amendment = InterventionAmendment.objects.create(
            intervention=self.intervention,
            types=[InterventionAmendment.RESULTS],
        )
        self.location = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 2")
        )

    def test_api_partners_list(self):
        response = self.forced_auth_req('get', '/api/v2/partners/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("Partner", response.data[0]["name"])

    @skip("different endpoint")
    def test_api_agreements_list(self):

        response = self.forced_auth_req('get', '/api/partners/' + str(self.partner.id) +
                                        '/agreements/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("PCA", response.data[0]["agreement_type"])


class TestAgreementCreateAPIView(APITenantTestCase):
    '''Exercise the create portion of the API.'''
    def setUp(self):
        self.partner = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        partner_staff = PartnerStaffFactory(partner=self.partner)

        self.partnership_manager_user = UserFactory(is_staff=True)
        self.partnership_manager_user.groups.add(GroupFactory())
        self.partnership_manager_user.profile.partner_staff_member = partner_staff.id
        self.partnership_manager_user.save()

    def test_minimal_create(self):
        '''Test passing as few fields as possible to create'''
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check for activity action created
        stream = model_stream(Agreement)
        self.assertEqual(len(stream), 1)
        self.assertEqual(stream[0].verb, 'created')
        self.assertIsNone(stream[0].target.start)

    def test_create_simple_fail(self):
        '''Verify that failing gives appropriate feedback'''
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIsInstance(response.data, dict)
        self.assertEqual(response.data.keys(), ['country_programme'])
        self.assertIsInstance(response.data['country_programme'], list)
        self.assertEqual(response.data['country_programme'][0], 'Country Programme is required for PCAs!')

        # Check that no activity action was created
        self.assertEqual(len(model_stream(Agreement)), 0)


class TestAgreementAPIFileAttachments(APITenantTestCase):
    '''Test retrieving attachments to agreements and agreement amendments. The file-specific fields are read-only
    on the relevant serializers, so they can't be edited through the API.
    '''
    def setUp(self):
        self.partner = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            partner=self.partner,
            attached_agreement=None,
        )

    def _get_and_assert_response(self):
        '''Helper method to get the agreement and verify some basic about the response JSON (which it returns).'''
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
        '''Exercise getting agreement attachment and agreement amendment attachments both when they're present
        and absent.
        '''
        # The agreement starts with no attachment.
        response_json = self._get_and_assert_response()
        self.assertIsNone(response_json['attached_agreement_file'])

        # Now add an attachment. Note that in Python 2, the content must be str, in Python 3 the content must be
        # bytes. I think the existing code is compatible with both.
        self.agreement.attached_agreement = SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8'))
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
        expected_path_components = ['',
                                    settings.MEDIA_URL.strip('/'),
                                    connection.schema_name,
                                    'file_attachments',
                                    'partner_organization',
                                    str(self.agreement.partner.id),
                                    'agreements',
                                    # Note that slashes have to be stripped from the agreement number to match the
                                    # normalized path.
                                    self.agreement.agreement_number.strip('/'),
                                    ]
        self.assertEqual(expected_path_components, url.path.split('/')[:-1])

        # Confirm that there are no amendments as of yet.
        self.assertIn('amendments', response_json)
        self.assertEqual(response_json['amendments'], [])

        # Now add an amendment.
        amendment = AgreementAmendmentFactory(agreement=self.agreement, signed_amendment=None)
        amendment.signed_amendment = SimpleUploadedFile('goodbye_world.txt', u'goodbye world!'.encode('utf-8'))
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
        expected_path_components = ['',
                                    settings.MEDIA_URL.strip('/'),
                                    connection.schema_name,
                                    'file_attachments',
                                    'partner_org',
                                    str(self.agreement.partner.id),
                                    'agreements',
                                    self.agreement.base_number.strip('/'),
                                    'amendments',
                                    amendment.number.strip('/'),
                                    ]
        self.assertEqual(expected_path_components, url.path.split('/')[:-1])


class TestAgreementAPIView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        self.partner_staff = PartnerStaffFactory(partner=self.partner)
        self.partner_staff2 = PartnerStaffFactory(partner=self.partner)

        self.partner_staff_user = UserFactory(is_staff=True)
        self.partner_staff_user.profile.partner_staff_member = self.partner_staff.id
        self.partner_staff_user.save()

        self.partnership_manager_user = UserFactory(is_staff=True)
        self.partnership_manager_user.groups.add(GroupFactory())
        self.partnership_manager_user.profile.partner_staff_member = self.partner_staff.id
        self.partnership_manager_user.save()

        today = datetime.date.today()
        self.country_programme = CountryProgrammeFactory(
            from_date=date(today.year - 1, 1, 1),
            to_date=date(today.year + 1, 1, 1))

        attached_agreement = "agreement.pdf"
        self.agreement = AgreementFactory(
            partner=self.partner,
            partner_manager=self.partner_staff,
            country_programme=self.country_programme,
            start=datetime.date.today(),
            end=self.country_programme.to_date,
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            signed_by=self.unicef_staff,
            attached_agreement=attached_agreement,
        )
        self.agreement.authorized_officers.add(self.partner_staff)
        self.agreement.save()

        self.amendment1 = AgreementAmendment.objects.create(
            number="001",
            agreement=self.agreement,
            signed_amendment="application/pdf",
            signed_date=datetime.date.today(),
            types=[AgreementAmendment.IP_NAME]
        )
        self.amendment2 = AgreementAmendment.objects.create(
            number="002",
            agreement=self.agreement,
            signed_amendment="application/pdf",
            signed_date=datetime.date.today(),
            types=[AgreementAmendment.BANKING_INFO]
        )
        self.agreement2 = AgreementFactory(
            partner=self.partner,
            agreement_type=Agreement.MOU,
            status=Agreement.DRAFT,
        )
        self.intervention = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD)

    def test_cp_end_date_update(self):
        data = {
            'agreement_type': Agreement.PCA,
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
            user=self.partner_staff_user,
            data=data
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response_json:
            self.assertEqual(r['end'], self.country_programme.to_date.isoformat())

        self.country_programme.to_date = self.country_programme.to_date + timedelta(days=1)
        self.country_programme.save()
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
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
            '/api/v2/agreements/',
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])

    def test_null_update_generates_no_activity_stream(self):
        '''Verify that a do-nothing update doesn't create anything in the model's activity stream'''
        data = {
            "agreement_number": self.agreement.agreement_number
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(model_stream(Agreement).count(), 0)

    def test_agreements_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["agreement_number"], self.agreement.agreement_number)

    def test_agreements_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["authorized_officers"][0]["first_name"], self.partner_staff.first_name)

    def test_agreements_update_partner_staff(self):
        data = {
            "authorized_officers": [
                self.partner_staff.id,
                self.partner_staff2.id
            ],
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["authorized_officers"]), 2)

        # Check for activity action created
        self.assertEqual(model_stream(Agreement).count(), 1)
        self.assertEqual(model_stream(Agreement)[0].verb, 'changed')

    def test_agreements_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agreements_list_filter_type(self):
        params = {"agreement_type": Agreement.PCA}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
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
            '/api/v2/agreements/',
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
            '/api/v2/agreements/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(self.partner.name, response.data[0]["partner_name"])

    def test_agreements_list_filter_search(self):
        params = {"search": "Partner"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
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
            '/api/v2/agreements/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # self.assertEqual(response.data[1]["agreement_number"], self.agreement.agreement_number)

    def test_agreements_update_set_to_active_on_save(self):
        '''Ensure that a draft agreement auto-transitions to signed when saved with signing info'''
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            status=Agreement.DRAFT,
            partner=self.partner,
            partner_manager=self.partner_staff,
            start=datetime.date.today(),
            end=self.country_programme.to_date,
            signed_by=None,
        )
        # In order to auto-transition to signed, this agreement needs authorized officers
        agreement.authorized_officers.add(self.partner_staff)
        agreement.save()

        today = datetime.date.today()
        data = {
            "start": today - datetime.timedelta(days=5),
            "end": today + datetime.timedelta(days=5),
            "signed_by": self.unicef_staff.id,
            "signed_by_unicef_date": datetime.date.today(),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(agreement.id),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Agreement.SIGNED)

    def test_partner_agreements_update_suspend(self):
        '''Ensure that interventions related to an agreement are suspended when the agreement is suspended'''
        # There's a limited number of statuses that the intervention can have in order to transition to suspended;
        # signed is one of them.
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()

        data = {
            "status": Agreement.SUSPENDED,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Agreement.SUSPENDED)
        self.assertEqual(Intervention.objects.get(agreement=self.agreement).status, Intervention.SUSPENDED)

    def test_agreement_amendment_delete_error(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/amendments/{}/'.format(self.agreement.amendments.first().id),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete a signed amendment"])

    def test_agreement_generate_pdf_default(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/generate_doc/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agreement_generate_pdf_lang(self):
        params = {
            "lang": "spanish",
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/generate_doc/'.format(self.agreement.id),
            user=self.unicef_staff,
            data=params
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["amendments"][1]["types"]), 2)


class TestPartnerStaffMemberAPIView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        self.partner_staff = PartnerStaffFactory(partner=self.partner)
        self.partner_staff_user = UserFactory(is_staff=True)
        self.partner_staff_user.groups.add(GroupFactory())
        self.partner_staff_user.profile.partner_staff_member = self.partner_staff.id
        self.partner_staff_user.profile.save()

    @skip("different endpoint")
    def test_partner_retrieve_embedded_staffmembers(self):
        response = self.forced_auth_req(
            'get',
            '/api/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Partner", response.data["name"])
        self.assertEqual("Mace", response.data["staff_members"][0]["first_name"])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_create_non_active(self):
        data = {
            "email": "a@aaa.com",
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/staff-members/',
            user=self.partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"],
                         ["New Staff Member needs to be active at the moment of creation"])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_create_already_partner(self):
        partner = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        partner_staff = PartnerStaffFactory(partner=partner)
        partner_staff_user = UserFactory(is_staff=True)
        partner_staff_user.profile.partner_staff_member = partner_staff.id
        partner_staff_user.profile.save()
        data = {
            "email": partner_staff_user.email,
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar",
            "active": True
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/staff-members/',
            user=partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "The email for the partner contact is used by another partner contact. Email has to be unique to proceed",
            response.data["non_field_errors"][0])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_create(self):
        data = {
            "email": "a@aaa.com",
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar",
            "active": True,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/staff-members/',
            user=self.partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Mace")

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_update(self):
        data = {
            "email": self.partner_staff.email,
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar updated",
            "active": True,
        }
        response = self.forced_auth_req(
            'put',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "foobar updated")

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_update_email(self):
        data = {
            "email": "a@a.com",
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar updated",
            "active": True,
        }
        response = self.forced_auth_req(
            'put',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("User emails cannot be changed, please remove the user and add another one",
                      response.data["non_field_errors"][0])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_retrieve_properties(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/staff-members/{}/properties/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestInterventionViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.partnership_manager_user.groups.add(GroupFactory())
        self.agreement = AgreementFactory()
        self.agreement2 = AgreementFactory(status="draft")
        self.partnerstaff = PartnerStaffFactory(partner=self.agreement.partner)
        data = {
            "document_type": Intervention.SHPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.partnership_manager_user,
            data=data
        )
        self.intervention = response.data

        self.sector = Sector.objects.create(name="Sector 1")
        self.location = LocationFactory()
        self.isll = InterventionSectorLocationLink.objects.create(
            intervention=Intervention.objects.get(id=self.intervention["id"]),
            sector=self.sector,
        )
        self.isll.locations.add(LocationFactory())
        self.isll.save()
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

        # Basic data to adjust in tests
        self.intervention_data = {
            "agreement": self.agreement2.id,
            "partner_id": self.agreement2.partner.id,
            "document_type": Intervention.SHPD,
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
                    "audit": 1
                },
            ],
            "planned_budget":
                {
                    "partner_contribution": "2.00",
                    "unicef_cash": "3.00",
                    "in_kind_amount": "1.00",
                    "partner_contribution_local": "3.00",
                    "unicef_cash_local": "3.00",
                    "in_kind_amount_local": "0.00",
                    "total": "6.00"
                },
            "sector_locations": [
                {
                    "sector": self.sector.id,
                    "locations": [self.location.id],
                }
            ],
            "result_links": [
                {
                    "cp_output": ResultFactory().id,
                    "ram_indicators": []
                }
            ],
            "amendments": [],
            "attachments": [],
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.partnership_manager_user,
            data=self.intervention_data
        )
        self.intervention_data = response.data
        self.intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        self.planned_visit = InterventionPlannedVisits.objects.create(
            intervention=self.intervention_obj
        )
        attachment = "attachment.pdf"
        self.attachment = InterventionAttachment.objects.create(
            intervention=self.intervention_obj,
            attachment=attachment,
            type=FileType.objects.create(name="pdf")
        )
        self.result = InterventionResultLink.objects.create(
            intervention=self.intervention_obj,
            cp_output=ResultFactory(),
        )
        amendment = "amendment.pdf"
        self.amendment = InterventionAmendment.objects.create(
            intervention=self.intervention_obj,
            types=[InterventionAmendment.RESULTS],
            signed_date=datetime.date.today(),
            signed_amendment=amendment
        )
        self.sector = Sector.objects.create(name="Sector 2")
        self.location = LocationFactory()
        self.isll = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention_obj,
            sector=self.sector,
        )
        self.isll.locations.add(LocationFactory())
        self.isll.save()
        self.intervention_obj.status = Intervention.DRAFT
        self.intervention_obj.save()

    def test_intervention_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_intervention_list_minimal(self):
        params = {"verbosity": "minimal"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].keys(), ["id", "title"])

    def test_intervention_create(self):
        data = {
            "document_type": Intervention.SHPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP Updated",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.partnership_manager_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check for activity action created
        self.assertEqual(model_stream(Intervention).count(), 3)
        self.assertEqual(model_stream(Intervention)[0].verb, 'created')

    def test_intervention_create_unicef_user_fail(self):
        data = {
            "document_type": Intervention.SHPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP Updated fail",
            "start": (timezone.now().date()).isoformat(),
            "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], u'Accessing this item is not allowed.')

    def test_intervention_retrieve_fr_numbers(self):
        self.fr_header_1.intervention = self.intervention_obj
        self.fr_header_2.intervention = self.intervention_obj
        self.fr_header_1.save()
        self.fr_header_2.save()

        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
        )
        r_data = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r_data["frs_details"]['frs']), 2)
        self.assertItemsEqual(r_data["frs"], [self.fr_header_2.id, self.fr_header_1.id])

    def test_intervention_active_update_population_focus(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        self.intervention_data.update(population_focus=None)
        self.intervention_data.update(status="active")
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
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
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
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
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot change fields while intervention is active: unicef_cash"])

    @skip('TODO: update test when new validation requirement is built')
    def test_intervention_active_update_sector_locations(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        InterventionSectorLocationLink.objects.filter(intervention=self.intervention_data.get("id")).delete()
        self.intervention_data.update(sector_locations=[])
        self.intervention_data.update(status="active")
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Sector locations are required if Intervention status is ACTIVE or IMPLEMENTED."])

    def test_intervention_validation(self):
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.partnership_manager_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data,
                         {"document_type": ["This field is required."],
                          "agreement": ["This field is required."],
                          "title": ["This field is required."]})

    def test_intervention_validation_doctype_pca(self):
        data = {
            "document_type": Intervention.SSFA,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(u'Agreement selected is not of type SSFA', response.data)

    def test_intervention_validation_doctype_ssfa(self):
        self.agreement.agreement_type = Agreement.SSFA
        self.agreement.save()
        data = {
            "document_type": Intervention.PD,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Document type PD or SHPD can only be associated with a PCA agreement.', response.data)

    def test_intervention_validation_dates(self):
        today = datetime.date.today()
        data = {
            "start": datetime.date(today.year + 1, 1, 1),
            "end": today,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['Start date must precede end date'])

    def test_intervention_update_planned_visits(self):
        import copy
        a = copy.deepcopy(self.intervention_data["planned_visits"])
        a.append({
            "year": 2015,
            "programmatic": 2,
            "spot_checks": 1,
            "audit": 1
        })
        data = {
            "planned_visits": a,
        }

        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.partnership_manager_user,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_intervention_filter(self):
        # Test filter
        params = {
            "partnership_type": Intervention.PD,
            "status": Intervention.DRAFT,
            "start": "2016-10-28",
            "end": "2016-10-28",
            "location": "Location",
            "sector": self.sector.id,
            "search": "2009",
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
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
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_intervention_planned_visits_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/planned-visits/{}/'.format(self.planned_visit.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_planned_visits_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = Intervention.ACTIVE
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/planned-visits/{}/'.format(self.planned_visit.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a planned visit"])

    def test_intervention_attachments_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/attachments/{}/'.format(self.attachment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_attachments_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = "active"
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/attachments/{}/'.format(self.attachment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete an attachment"])

    def test_intervention_results_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/results/{}/'.format(self.result.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_results_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = Intervention.ACTIVE
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/results/{}/'.format(self.result.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a result"])

    def test_intervention_amendments_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/amendments/{}/'.format(self.amendment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_amendments_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = Intervention.ACTIVE
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/amendments/{}/'.format(self.amendment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete an amendment"])

    def test_intervention_sector_locations_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/sector-locations/{}/'.format(self.isll.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_sector_locations_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = Intervention.ACTIVE
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/sector-locations/{}/'.format(self.isll.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a sector location"])

    def test_api_interventions_values(self):
        params = {"values": "{}".format(self.intervention["id"])}
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.intervention["id"])


class TestPartnershipDashboardView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.agreement = AgreementFactory()
        self.agreement2 = AgreementFactory(status=Agreement.DRAFT)
        self.partnerstaff = PartnerStaffFactory(partner=self.agreement.partner)
        data = {
            "document_type": Intervention.SHPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP",
            "start": "2016-10-28",
            "end": "2016-10-28",
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=data
        )
        self.intervention = response.data

        self.sector = Sector.objects.create(name="Sector 1")
        self.location = LocationFactory()
        self.isll = InterventionSectorLocationLink.objects.create(
            intervention=Intervention.objects.get(id=self.intervention["id"]),
            sector=self.sector,
        )
        self.isll.locations.add(LocationFactory())
        self.isll.save()

        # Basic data to adjust in tests
        self.intervention_data = {
            "agreement": self.agreement2.id,
            "partner_id": self.agreement2.partner.id,
            "document_type": Intervention.SHPD,
            "title": "2009 EFY AWP Updated",
            "status": Intervention.DRAFT,
            "start": "2017-01-28",
            "end": "2019-01-28",
            "submission_date_prc": "2017-01-31",
            "review_date_prc": "2017-01-28",
            "submission_date": "2017-01-28",
            "prc_review_document": None,
            "signed_by_unicef_date": "2017-01-28",
            "signed_by_partner_date": "2017-01-20",
            "unicef_signatory": self.unicef_staff.id,
            "unicef_focal_points": [],
            "partner_focal_points": [],
            "partner_authorized_officer_signatory": self.partnerstaff.id,
            "offices": [],
            "fr_numbers": None,
            "population_focus": "Some focus",
            "planned_budget":
                {
                    "partner_contribution": "2.00",
                    "unicef_cash": "3.00",
                    "in_kind_amount": "1.00",
                    "partner_contribution_local": "3.00",
                    "unicef_cash_local": "3.00",
                    "in_kind_amount_local": "0.00",
                    "total": "6.00"
                },
            "sector_locations": [
                {
                    "sector": self.sector.id,
                    "locations": [self.location.id],
                }
            ],
            "result_links": [
                {
                    "cp_output": ResultFactory().id,
                    "ram_indicators": []
                }
            ],
            "amendments": [],
            "attachments": [],
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=self.intervention_data
        )
        self.intervention_data = response.data
