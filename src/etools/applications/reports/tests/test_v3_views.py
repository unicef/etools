from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.reports.models import Section
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.users.tests.factories import UserFactory


class TestPMPSectionViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        cls.partner_staff = cls.partner.staff_members.all().first()
        cls.partner_user = UserFactory(email=cls.partner_staff.email)
        cls.partner_user.profile.partner_staff_member = True
        cls.partner_user.profile.save()

    def test_list(self):
        for __ in range(10):
            SectionFactory()
        section = SectionFactory()
        pd = InterventionFactory()
        pd.sections.add(section)
        pd.partner_focal_points.add(self.partner_staff)

        url = reverse('sections-pmp-list')
        section_qs = Section.objects
        self.assertTrue(section_qs.count() > 10)

        # unicef staff
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), section_qs.count())

        # partner
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]["id"]), str(section.pk))

    def test_detail(self):
        section = SectionFactory()

        # unicef staff
        url = reverse('sections-pmp-detail', args=[section.pk])
        response = self.forced_auth_req('get', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # partner not associated
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # partner
        pd = InterventionFactory()
        pd.sections.add(section)
        pd.partner_focal_points.add(self.partner_staff)
        response = self.forced_auth_req('get', url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
