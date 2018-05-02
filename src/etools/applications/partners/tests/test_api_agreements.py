import datetime
import json

from django.core.urlresolvers import reverse
from django.test import SimpleTestCase

from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import Agreement, AgreementAmendment, Intervention, PartnerType
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.snapshot.models import Activity
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    '''Simple test case to verify URL reversal'''

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('agreement-list', '', {}),
            ('agreement-detail', '1/', {'pk': 1}),
            ('pca_pdf', '1/generate_doc/', {'agr': 1}),
            ('agreement-amendment-del', 'amendments/1/', {'pk': 1}),
            ('agreement-amendment-list', 'amendments/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/agreements/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestAgreementsAPI(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partnership_manager_user = UserFactory(is_staff=True)
        cls.partnership_manager_user.groups.add(GroupFactory())

        cls.partner1 = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        cls.country_programme = CountryProgrammeFactory()
        cls.agreement1 = AgreementFactory(partner=cls.partner1, signed_by_unicef_date=datetime.date.today())
        cls.intervention = InterventionFactory(agreement=cls.agreement1)
        cls.intervention_2 = InterventionFactory(agreement=cls.agreement1, document_type=Intervention.PD)
        cls.amendment = AgreementAmendment.objects.create(agreement=cls.agreement1,
                                                          types=[AgreementAmendment.IP_NAME,
                                                                 AgreementAmendment.CLAUSE],
                                                          number="001",
                                                          signed_amendment="application/pdf",
                                                          signed_date=datetime.date.today())

    def run_request_list_ep(self, data={}, user=None, method='post'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:agreement-list'),
            user=user or self.partnership_manager_user,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request(self, agreement_id, data=None, method='get', user=None):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:agreement-detail', kwargs={'pk': agreement_id}),
            user=user or self.partnership_manager_user,
            data=data or {}
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_add_new_PCA(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.PCA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_fail_add_new_PCA_without_agreement_type(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['agreement_type'], ['This field is required.'])
        self.assertFalse(Activity.objects.exists())

    def test_fail_add_new_PCA_without_country_programme(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['country_programme'], ['Country Programme is required for PCAs!'])
        self.assertFalse(Activity.objects.exists())

    def test_add_new_SSFA_without_country_programme(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.SSFA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_add_new_SSFA_with_country_programme_null(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id,
            "country_programme": 'null'
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.SSFA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_fail_patch_PCA_without_country_programme(self):
        # create new agreement
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id
        }
        status_code, response = self.run_request_list_ep(data)
        self.assertTrue(Activity.objects.exists())
        agreement_id = response['id']

        # change agreement type to a PCA
        data = {
            "agreement_type": Agreement.PCA
        }
        status_code, response = self.run_request(agreement_id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['country_programme'], ['Country Programme is required for PCAs!'])
        self.assertTrue(Activity.objects.exists())

    def test_fail_patch_PCA_without_PartnershipManagerPermission(self):
        # create new agreement
        # change agreement type to a PCA
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA
        }
        status_code, response = self.run_request(self.agreement1.id, data, method='patch', user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['detail'], 'Accessing this item is not allowed.')
        self.assertFalse(Activity.objects.exists())

    def test_fail_add_PCA_without_PartnershipManagerPermission(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
        }
        status_code, response = self.run_request_list_ep(data, user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['detail'], 'Accessing this item is not allowed.')
        self.assertFalse(Activity.objects.exists())

    def test_list_agreements(self):
        with self.assertNumQueries(1):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)
