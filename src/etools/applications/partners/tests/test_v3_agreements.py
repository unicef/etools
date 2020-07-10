import datetime

from django.test import SimpleTestCase
from django.urls import reverse

from rest_framework import status
from unicef_snapshot.models import Activity

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import Agreement, PartnerType
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('agreement-list', '', {}),
            ('agreement-detail', '1/', {'pk': 1}),
        )
        self.assertReversal(
            names_and_paths,
            'pmp_v3:',
            '/api/pmp/v3/agreements/',
        )
        self.assertIntParamRegexes(names_and_paths, 'pmp_v3:')


class TestCreate(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pme_user = UserFactory(is_staff=True)
        cls.pme_user.groups.add(GroupFactory())
        cls.partner = PartnerFactory(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
        )
        cls.country_programme = CountryProgrammeFactory()

    def test_post(self):
        activity_qs = Activity.objects.filter(action=Activity.CREATE)
        self.assertFalse(activity_qs.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner.pk,
            "country_programme": self.country_programme.pk,
            "reference_number_year": datetime.date.today().year,
        }
        response = self.forced_auth_req(
            "post",
            reverse('partners_api:agreement-list'),
            user=self.pme_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data['agreement_type'], Agreement.PCA)
        self.assertTrue(activity_qs.exists())
