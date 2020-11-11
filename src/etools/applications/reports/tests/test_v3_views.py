from django.test import override_settings
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.reports.models import Office, Section
from etools.applications.reports.tests.factories import OfficeFactory, SectionFactory
from etools.applications.reports.tests.test_views import SpecialReportingRequirementListCreateMixin
from etools.applications.users.tests.factories import UserFactory


class BasePMPTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        cls.partner_staff = cls.partner.staff_members.all().first()
        cls.partner_user = cls.partner_staff.user


class TestPMPOfficeViews(BasePMPTestCase):
    def setUp(self):
        super().setUp()
        for __ in range(10):
            OfficeFactory()
        self.office = OfficeFactory()
        pd = InterventionFactory()
        pd.offices.add(self.office)
        pd.partner_focal_points.add(self.partner_staff)

        self.url = reverse('offices-pmp-list')
        self.office_qs = Office.objects
        self.assertTrue(self.office_qs.count() > 10)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        # unicef staff
        self.assertTrue(self.user.is_unicef_user())
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), self.office_qs.count())

    def test_list_partner(self):
        # partner
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]["id"]), str(self.office.pk))

        # partner no interventions
        user = UserFactory(is_staff=False)
        response = self.forced_auth_req('get', self.url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_detail(self):
        office = OfficeFactory()

        # unicef staff
        response = self.forced_auth_req(
            'get',
            reverse('offices-pmp-detail', args=[office.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_partner(self):
        office = OfficeFactory()
        url = reverse('offices-pmp-detail', args=[office.pk])

        # partner not associated
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # partner
        pd = InterventionFactory()
        pd.offices.add(office)
        pd.partner_focal_points.add(self.partner_staff)
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestPMPSectionViews(BasePMPTestCase):
    def setUp(self):
        super().setUp()
        for __ in range(10):
            SectionFactory()
        self.section = SectionFactory()
        pd = InterventionFactory()
        pd.sections.add(self.section)
        pd.partner_focal_points.add(self.partner_staff)

        self.url = reverse('sections-pmp-list')
        self.section_qs = Section.objects
        self.assertTrue(self.section_qs.count() > 10)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        # unicef staff
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), self.section_qs.count())

    def test_list_partner(self):
        # partner
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]["id"]), str(self.section.pk))

        # partner no relationship
        user = UserFactory(is_staff=False)
        response = self.forced_auth_req('get', self.url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_detail(self):
        section = SectionFactory()

        # unicef staff
        response = self.forced_auth_req(
            'get',
            reverse('sections-pmp-detail', args=[section.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_partner(self):
        section = SectionFactory()
        url = reverse('sections-pmp-detail', args=[section.pk])

        # partner not associated
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # partner
        pd = InterventionFactory()
        pd.sections.add(section)
        pd.partner_focal_points.add(self.partner_staff)
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestPMPSpecialReportingRequirementListCreateView(
        SpecialReportingRequirementListCreateMixin,
        BaseTenantTestCase,
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse(
            "reports_v3:interventions-special-reporting-requirements",
            kwargs={'intervention_pk': cls.intervention.pk}
        )
