import datetime
from unittest import skip

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import AgreementFactory, PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('partner-list', '', {}),
            (
                'partner-staff-members-list',
                '1/staff-members/',
                {'partner_pk': 1},
            ),
        )
        self.assertReversal(
            names_and_paths,
            'pmp_v3:',
            '/api/pmp/v3/partners/',
        )
        self.assertIntParamRegexes(names_and_paths, 'pmp_v3:')


class BasePartnerOrganizationTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.unicef_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP],
        )
        self.partner = PartnerFactory(organization=OrganizationFactory(name='Partner 1', vendor_number="VP1"))
        self.agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today(),
        )


class TestPartnerOrganizationList(BasePartnerOrganizationTestCase):
    def test_list_for_unicef(self):
        PartnerFactory()
        with self.assertNumQueries(4):
            response = self.forced_auth_req(
                "get",
                reverse('pmp_v3:partner-list'),
                user=self.unicef_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data),
            PartnerOrganization.objects.count(),
        )

    def test_list_for_partner(self):
        partner = PartnerFactory()
        user = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=partner.organization
        )
        with self.assertNumQueries(5):
            response = self.forced_auth_req(
                "get",
                reverse('pmp_v3:partner-list'),
                user=user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], partner.pk)

    def test_not_authenticated(self):
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:partner-list'),
            user=AnonymousUser(),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip("waiting on update to partner permissions")
    def test_not_partner_user(self):
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:partner-list'),
            user=UserFactory(is_staff=False, realms__data=[]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestPartnerStaffMemberList(BasePartnerOrganizationTestCase):
    def test_list_for_unicef(self):
        partner = PartnerFactory()
        for __ in range(10):
            UserFactory(
                realms__data=['IP Viewer'],
                profile__organization=partner.organization
            )
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:partner-staff-members-list', args=[partner.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data),
            partner.all_staff_members.count(),
        )
        self.assertEqual(
            partner.all_staff_members.count(),
            10
        )

    def test_list_with_realm_active_inactive(self):
        partner = PartnerFactory()
        for __ in range(10):
            UserFactory(
                realms__data=['IP Viewer'],
                profile__organization=partner.organization
            )
        for __ in range(5):
            user = UserFactory(
                realms__data=['IP Editor'],
                profile__organization=partner.organization
            )
            user.realms.update(is_active=False)

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:partner-staff-members-list', args=[partner.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data),
            partner.all_staff_members.count(),
        )
        self.assertEqual(
            partner.all_staff_members.count(),
            15
        )
        self.assertEqual(
            partner.active_staff_members.count(),
            10
        )

    def test_list_for_partner(self):
        partner = PartnerFactory()
        for __ in range(10):
            user = UserFactory(
                realms__data=['IP Viewer'],
                profile__organization=partner.organization
            )

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:partner-staff-members-list', args=[partner.pk]),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data),
            partner.all_staff_members.count(),
        )
        self.assertEqual(
            partner.all_staff_members.count(),
            10
        )
        # partner user not able to view another partners users
        partner_2 = PartnerFactory()
        user_2 = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=partner_2.organization
        )
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:partner-staff-members-list', args=[partner.pk]),
            user=user_2,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_not_authenticated(self):
        response = self.forced_auth_req(
            "get",
            reverse(
                'pmp_v3:partner-staff-members-list',
                args=[self.partner.pk],
            ),
            user=AnonymousUser(),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip("waiting on update to partner permissions")
    def test_not_partner_user(self):
        response = self.forced_auth_req(
            "get",
            reverse(
                'pmp_v3:partner-staff-members-list',
                args=[self.partner.pk],
            ),
            user=UserFactory(is_staff=False, realms__data=[]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
