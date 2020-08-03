import datetime

from django.test import SimpleTestCase
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory, FundsReservationItemFactory
from etools.applications.partners.models import Intervention, InterventionManagementBudget
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionFactory,
    InterventionManagementBudgetFactory,
    PartnerFactory,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('intervention-list', '', {}),
            ('intervention-detail', '1/', {'pk': 1}),
        )
        self.assertReversal(
            names_and_paths,
            'pmp_v3:',
            '/api/pmp/v3/interventions/',
        )
        self.assertIntParamRegexes(names_and_paths, 'pmp_v3:')


class BaseInterventionTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True)
        self.user.groups.add(GroupFactory())
        self.partner = PartnerFactory(name='Partner 1', vendor_number="VP1")
        self.agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today(),
        )


class TestList(BaseInterventionTestCase):
    def test_get(self):
        intervention = InterventionFactory()
        frs = FundsReservationHeaderFactory(
            intervention=intervention,
            currency='USD',
        )
        FundsReservationItemFactory(fund_reservation=frs)
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], intervention.pk)


class TestCreate(BaseInterventionTestCase):
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
        i = Intervention.objects.get(pk=data.get("id"))
        self.assertTrue(i.humanitarian_flag)
        self.assertTrue(data.get("humanitarian_flag"))
        self.assertEqual(data.get("cfei_number"), "321")
        self.assertEqual(data.get("budget_owner"), self.user.pk)


class TestManagementBudgetGet(BaseInterventionTestCase):
    def test_get(self):
        intervention = InterventionFactory()
        budget_qs = InterventionManagementBudget.objects.filter(
            intervention=intervention,
        )
        assert not budget_qs.exists()
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        assert budget_qs.exists()
        assert data["act1_unicef"] is None
        assert data["act1_partner"] is None
        assert data["act2_unicef"] is None
        assert data["act2_partner"] is None
        assert data["act3_unicef"] is None
        assert data["act3_partner"] is None

    def test_put(self):
        intervention = InterventionFactory()
        budget_qs = InterventionManagementBudget.objects.filter(
            intervention=intervention,
        )
        assert not budget_qs.exists()
        response = self.forced_auth_req(
            "put",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={
                "act1_unicef": 1000,
                "act1_partner": 2000,
                "act2_unicef": 3000,
                "act2_partner": 4000,
                "act3_unicef": 5000,
                "act3_partner": 6000,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        assert budget_qs.exists()
        assert data["act1_unicef"] == "1000.00"
        assert data["act1_partner"] == "2000.00"
        assert data["act2_unicef"] == "3000.00"
        assert data["act2_partner"] == "4000.00"
        assert data["act3_unicef"] == "5000.00"
        assert data["act3_partner"] == "6000.00"

    def test_patch(self):
        intervention = InterventionFactory()
        InterventionManagementBudgetFactory(intervention=intervention)
        response = self.forced_auth_req(
            "patch",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={"act1_unicef": 1000},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        assert data["act1_unicef"] == "1000.00"
