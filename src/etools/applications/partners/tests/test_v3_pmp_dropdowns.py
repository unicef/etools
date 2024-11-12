from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class TestPMPDropdownsListApiView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.organization = OrganizationFactory()
        PartnerFactory(organization=cls.organization)
        cls.partner_user = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=cls.organization
        )
        cls.url = reverse('pmp_v3:dropdown-dynamic-list')
        cls.default_elements = [
            'agency_choices',
            'agreement_amendment_types',
            'agreement_status',
            'agreement_types',
            'assessment_types',
            'attachment_types',
            'attachment_types_active',
            'cash_transfer_modalities',
            'cp_outputs',
            'cso_types',
            'currencies',
            'file_types',
            'gdd_amendment_types',
            'gender_equity_sustainability_ratings',
            'intervention_amendment_types',
            'intervention_doc_type',
            'intervention_status',
            'local_currency',
            'location_types',
            'partner_file_types',
            'partner_risk_rating',
            'partner_types',
            'risk_types',
            'sea_risk_ratings',
            'supply_item_provided_by',
            'review_types',
        ]

    def test_unicef_data(self):
        with self.assertNumQueries(11):
            response = self.forced_auth_req('get', self.url, self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertListEqual(
            sorted(list(response.data.keys())),
            sorted([
                'signed_by_unicef_users',
                'country_programmes',
                'donors',
                'grants',
            ] + self.default_elements)
        )

    def test_partner_data(self):
        with self.assertNumQueries(10):
            response = self.forced_auth_req('get', self.url, self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertListEqual(
            sorted(list(response.data.keys())),
            sorted(self.default_elements),
        )

    def test_unknown_user(self):
        response = self.forced_auth_req('get', self.url, UserFactory(is_staff=False, realms__data=[]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_authentication(self):
        response = self.forced_auth_req('get', self.url, AnonymousUser())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
