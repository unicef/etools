import datetime

from django.test import override_settings, SimpleTestCase
from django.urls import reverse

from rest_framework import status
from tablib import Dataset
from unicef_snapshot.models import Activity

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import Agreement, PartnerType
from etools.applications.partners.tests.factories import AgreementFactory, PartnerFactory, PartnerStaffFactory
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


class BaseAgreementTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pme_user = UserFactory(is_staff=True)
        cls.pme_user.groups.add(GroupFactory())
        cls.partner_user = UserFactory(is_staff=False)
        cls.partner = PartnerFactory(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
        )
        cls.partner_staff = PartnerStaffFactory(
            partner=cls.partner,
            user=cls.partner_user,
        )
        cls.country_programme = CountryProgrammeFactory()
        cls.agreement = AgreementFactory(partner=cls.partner)
        cls.agreement.authorized_officers.add(cls.partner_staff)
        for __ in range(10):
            AgreementFactory()


class TestList(BaseAgreementTestCase):
    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_get(self):
        agreement_qs = Agreement.objects
        response = self.forced_auth_req(
            "get",
            reverse("pmp_v3:agreement-list"),
            user=self.pme_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        self.assertEqual(len(response.data), agreement_qs.count())

    def test_get_by_partner(self):
        agreement_qs = Agreement.objects.filter(partner=self.partner)
        response = self.forced_auth_req(
            "get",
            reverse("pmp_v3:agreement-list"),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        self.assertEqual(len(response.data), agreement_qs.count())

    def test_get_by_partner_not_related(self):
        staff = PartnerStaffFactory()
        response = self.forced_auth_req(
            "get",
            reverse("pmp_v3:agreement-list"),
            user=staff.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_filter_partner_id(self):
        agreement = AgreementFactory(partner=self.partner)
        agreement.authorized_officers.add(self.partner_staff)
        agreement_qs = Agreement.objects.filter(partner=self.partner)
        response = self.forced_auth_req(
            "get",
            reverse("pmp_v3:agreement-list"),
            user=self.partner_user,
            partner_id=self.partner.pk,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), agreement_qs.count())
        for data in response.data:
            self.assertEqual(data["partner"], self.partner.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_export_csv(self):
        AgreementFactory()
        response = self.forced_auth_req(
            "get",
            reverse("pmp_v3:agreement-list"),
            user=self.pme_user,
            data={"format": "csv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), "csv")
        self.assertEqual(dataset.height, Agreement.objects.count())
        self.assertEqual(
            dataset._get_headers(),
            [
                'Reference Number',
                'Status',
                'Partner Name',
                'partner_number',
                'Agreement Type',
                'Start Date',
                'End Date',
                'partner_manager_name',
                'Signed By Partner Date',
                'signed_by_name',
                'Signed By UNICEF Date',
                'staff_members',
                'amendments',
                'url',
                'Special Conditions PCA',
            ]
        )


class TestCreate(BaseAgreementTestCase):
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
            reverse('pmp_v3:agreement-list'),
            user=self.pme_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data['agreement_type'], Agreement.PCA)
        self.assertTrue(activity_qs.exists())

    def test_post_by_partner(self):
        activity_qs = Activity.objects.filter(action=Activity.CREATE)
        self.assertFalse(activity_qs.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner.pk,
            "country_programme": self.country_programme.pk,
            "reference_number_year": datetime.date.today().year,
            "signed_by": self.pme_user.pk,
        }
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:agreement-list'),
            user=self.partner_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(activity_qs.exists())


class TestUpdate(BaseAgreementTestCase):
    def test_patch(self):
        agreement = AgreementFactory(
            partner=self.partner,
            agreement_type=Agreement.SSFA,
            status=Agreement.DRAFT,
            signed_by=self.pme_user,
            start=datetime.date.today(),
        )
        agreement.authorized_officers.add(self.partner_staff)
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:agreement-detail', args=[agreement.pk]),
            user=self.partner_user,
            data={
                "reference_number_year": 2020,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agreement.refresh_from_db()
        self.assertEqual(agreement.reference_number_year, 2020)
