import datetime

from django.test import SimpleTestCase
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import AgreementFactory, PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('intervention-list', '', {}),
        )
        self.assertReversal(
            names_and_paths,
            'pmp_v3:',
            '/api/pmp/v3/interventions/',
        )
        self.assertIntParamRegexes(names_and_paths, 'pmp_v3:')


class TestCreate(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True)
        self.user.groups.add(GroupFactory())
        self.partner = PartnerFactory(name='Partner 1', vendor_number="VP1")
        self.agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today(),
        )

    def test_post(self):
        data = {
            "document_type": Intervention.PD,
            "title": "PMP Intervention",
            "contingency_pd": True,
            "agreement": self.agreement.pk,
            "reference_number_year": datetime.date.today().year,
            "humanitarian_flag": True,
            "cfei_number": "321",
            "budget_owner": self.user.pk,
        }
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        data.pop("permissions")
        i = Intervention.objects.get(pk=data.get("id"))
        self.assertTrue(data.get("humanitarian_flag"))
        self.assertEqual(data.get("cfei_number"), "321")
        self.assertEqual(data.get("budget_owner"), self.user.pk)
