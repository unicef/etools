import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.urls import reverse

from rest_framework import status

from etools.applications.action_points.models import PME
from etools.applications.audit.models import Auditor, UNICEFAuditFocalPoint, UNICEFUser
from etools.applications.audit.tests.factories import AuditFocalPointUserFactory, AuditorUserFactory, EngagementFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.tpm.models import ThirdPartyMonitor
from etools.applications.tpm.tests.factories import (
    BaseTPMVisitFactory,
    SimpleTPMPartnerFactory,
    TPMPartnerFactory,
    TPMUserFactory,
)
from etools.applications.users.mixins import GroupEditPermissionMixin, ORGANIZATION_GROUP_MAP
from etools.applications.users.models import (
    IPAdmin,
    IPAuthorizedOfficer,
    IPEditor,
    IPViewer,
    PartnershipManager,
    StagedUser,
    User,
    UserProfile,
    UserReviewer,
)
from etools.applications.users.serializers_v3 import AP_ALLOWED_COUNTRIES
from etools.applications.users.tests.factories import (
    GroupFactory,
    PMEUserFactory,
    ProfileFactory,
    RealmFactory,
    StagedUserFactory,
    UserFactory,
)
from etools.libraries.djangolib.models import GroupWrapper


class TestCountryView(BaseTenantTestCase):
    def test_get(self):
        user = UserFactory(is_staff=True)
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], user.profile.country.pk)

    def test_get_no_result(self):
        user = UserFactory(is_staff=True, profile__country=None)
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestOrganizationListView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        # clearing groups cache
        GroupWrapper.invalidate_instances()

        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partnership_manager = UserFactory(realms__data=[UNICEF_USER, PartnershipManager.name])

    def setUp(self):
        super().setUp()
        self.url = reverse('users_v3:organization-list')

    def test_get_forbidden_403(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=AuditorUserFactory(),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_partners_hidden(self):
        # organization without a related tenant partner will be filtered out
        OrganizationFactory()

        # marked for deletion tenant Partner will be filtered out
        organization1 = OrganizationFactory()
        PartnerFactory(organization=organization1, hidden=True)

        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_partners_200(self):
        organization = OrganizationFactory()
        PartnerFactory(organization=organization)

        with self.assertNumQueries(2):
            response = self.forced_auth_req(
                "get",
                self.url,
                user=self.partnership_manager,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], organization.id)

    def test_get_auditor_firms(self):
        PartnerFactory(organization=OrganizationFactory())
        engagement = EngagementFactory()
        with self.assertNumQueries(3):
            response = self.forced_auth_req(
                "get",
                self.url,
                data={"organization_type": "audit"},
                user=self.partnership_manager,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], engagement.agreement.auditor_firm.organization.id)

    def test_get_tpm_firms(self):
        PartnerFactory(organization=OrganizationFactory())
        EngagementFactory()
        tpm_visit = BaseTPMVisitFactory()
        with self.assertNumQueries(3):
            response = self.forced_auth_req(
                "get",
                self.url,
                data={"organization_type": "tpm"},
                user=self.partnership_manager,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], tpm_visit.tpm_partner.organization.id)


class TestChangeUserOrganizationView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("users_v3:organization-change")

    def test_post_organization_403(self):
        self.unicef_staff.refresh_from_db()
        self.assertEqual(self.unicef_staff.profile.organization.name, 'UNICEF')
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"organization": OrganizationFactory().pk}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post(self):
        another_org = OrganizationFactory()
        RealmFactory(user=self.unicef_staff, organization=another_org, group=IPAdmin.as_group())
        self.assertEqual(self.unicef_staff.profile.organization.name, 'UNICEF')

        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"organization": another_org.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.unicef_staff.profile.organization, another_org)


class TestUsersDetailAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_get_not_staff(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:user-detail", args=[self.unicef_staff.pk]),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.unicef_staff.username)

    def test_get(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:user-detail", args=[user.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], user.username)

    def test_get_not_found(self):
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:user-detail", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})


class TestUsersListAPIView(BaseTenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        self.url = reverse("users_v3:users-list")

    def test_not_staff(self):
        user = UserFactory(is_staff=False)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_api_users_list(self):
        with self.assertNumQueries(5):
            response = self.forced_auth_req('get', self.url, user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_forced_pagination(self):
        [UserFactory(is_staff=True) for _i in range(15)]
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff, data={'page': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 17)

    def test_forced_pagination_custom_page_size(self):
        [UserFactory(is_staff=True) for _i in range(15)]
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff, data={'page': 1, 'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_search(self):
        UserFactory(is_staff=True, email='test_user_email@example.com', realms__data=[])
        UserFactory(is_staff=True, email='test_user@example.com', realms__data=[])
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff, data={'search': 'test_user_email'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], 'test_user_email@example.com')

    def test_users_api_list_values(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"values": "{},{}".format(self.partnership_manager_user.id, self.unicef_superuser.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_api_users_list_values_bad(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"values": '1],2fg'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['Query parameter values are not integers'])

    def test_api_users_list_managers(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"partnership_managers": True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_api_users_retrieve_myprofile(self):
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:myprofile-detail"),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.unicef_staff.get_full_name())

    def test_api_users_retrieve_myprofile_show_ap_false(self):
        self.assertNotIn(self.unicef_staff.profile.country.name, AP_ALLOWED_COUNTRIES)
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:myprofile-detail"),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["show_ap"], False)

    def test_api_users_retrieve_myprofile_show_ap(self):
        self.unicef_staff.profile.country.name = AP_ALLOWED_COUNTRIES[0]
        self.unicef_staff.profile.country.save()
        self.assertIn(self.unicef_staff.profile.country.name, AP_ALLOWED_COUNTRIES)
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:myprofile-detail"),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["show_ap"], True)

    def test_minimal_verbosity(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'verbosity': 'minimal'},
            user=self.unicef_staff
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 2)
        self.assertEqual(
            sorted([self.unicef_staff.id, self.partnership_manager_user.id]),
            sorted(map(lambda x: x['id'], response_json)))

    def test_partner_user(self):
        partner = PartnerFactory()
        partner_user = UserFactory(
            realms__data=['IP Viewer'], profile__organization=partner.organization
        )
        self.assertEqual(partner_user, partner.active_staff_members.all().first())
        self.assertTrue(get_user_model().objects.count() > 1)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=partner_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], partner_user.pk)


class TestMyProfileAPIView(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.url = reverse("users_v3:myprofile-detail")

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["name"],
            self.unicef_staff.get_full_name()
        )
        self.assertEqual(response.data["is_superuser"], False)

    def test_get_no_profile(self):
        """Ensure profile is created for user, if it does not exist"""
        user = self.unicef_staff
        UserProfile.objects.get(user=user).delete()
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

        # We need user.profile to NOT return a profile, otherwise the view will
        # still see the deleted one and not create a new one.  (This is only a
        # problem for this test, not in real usage.)
        # ``user.refresh_from_db()`` does not seem sufficient to stop user.profile from
        # returning the now-deleted profile object, so do it the hard way.
        # (Hopefully this is fixed, but here in Django 1.10.8 it's a problem.
        # And I don't see any mention of a fix in release notes up through
        # 2.0.3.)
        user = get_user_model().objects.get(pk=user.pk)

        response = self.forced_auth_req(
            "get",
            self.url,
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], user.get_full_name())
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_patch(self):
        self.assertNotEqual(
            self.unicef_staff.profile.oic,
            self.unicef_superuser
        )
        data = {
            "oic": self.unicef_superuser.id,
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)
        self.assertEqual(response.data["is_superuser"], False)

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)
        self.assertEqual(response.data["is_superuser"], False)

    def test_patch_preferences(self):
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )
        data = {
            "preferences": {
                "language": "fr"
            }
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], self.unicef_staff.preferences)
        self.assertEqual(self.unicef_staff.preferences, data['preferences'])

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], self.unicef_staff.preferences)

    def test_patch_preferences_unregistered_language(self):
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )
        data = {
            "preferences": {
                "language": "nonsense"
            }
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.data,
            {
                'preferences': {'language': ['"nonsense" is not a valid choice.']}
            }
        )

    def test_patch_nonexistent_preference(self):
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )
        data = {
            "preferences": {
                "nonexistent": "fr"
            }
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )


class TestGroupFiltersViewSet(BaseTenantTestCase):
    fixtures = ['amp_groups', 'audit_groups', 'tpm_groups']

    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory()

    def setUp(self):
        super().setUp()
        self.url = reverse("users_v3:amp-group-filters")

    def test_get_group_filters_partner_users(self):
        for user_group in [IPViewer, IPEditor, IPAuthorizedOfficer, IPAdmin]:
            user = UserFactory(realms__data=[user_group.name], profile__organization=self.organization)
            with self.assertNumQueries(3):
                response = self.forced_auth_req(
                    "get",
                    self.url,
                    user=user
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            for _type in ORGANIZATION_GROUP_MAP.keys():
                self.assertEqual(
                    list(Group.objects.filter(name__in=ORGANIZATION_GROUP_MAP[_type]).values_list('id', flat=True)),
                    [item['id'] for item in response.data[_type]]
                )


class TestGroupPermissionsViewSet(BaseTenantTestCase):
    fixtures = ['amp_groups', 'audit_groups']

    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory()
        cls.partner = PartnerFactory(organization=cls.organization)
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("users_v3:amp-group-permissions")

    def test_get_allowed_amp_groups_unicef(self):
        for user_group, org_type in zip(
                [UNICEFAuditFocalPoint, PartnershipManager],
                ['audit', 'partner', 'tpm']):
            user = UserFactory(realms__data=[user_group.name], profile__organization=self.organization)
            with self.assertNumQueries(4):
                response = self.forced_auth_req(
                    "get",
                    self.url,
                    data={'organization_type': org_type},
                    user=user
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            expected_groups = sorted(
                GroupEditPermissionMixin.GROUPS_ALLOWED_MAP.get(user_group.name, {}).get(org_type))

            actual_groups = sorted([group['name'] for group in response.data['groups']])
            self.assertEqual(expected_groups, actual_groups)
            self.assertEqual(response.data['can_add_user'], True)

    def test_get_allowed_amp_groups_partner(self):
        for user_group in [IPViewer, IPEditor, IPAuthorizedOfficer, IPAdmin]:
            response = self.forced_auth_req(
                "get",
                self.url,
                user=UserFactory(
                    realms__data=[user_group.name], profile__organization=self.organization
                )
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            expected_groups = sorted(
                GroupEditPermissionMixin.GROUPS_ALLOWED_MAP.get(user_group.name, {}).get(self.organization.relationship_types[0], []))
            actual_groups = sorted([group['name'] for group in response.data['groups']])
            self.assertEqual(expected_groups, actual_groups)
            self.assertEqual(
                response.data['can_add_user'],
                True if user_group in [IPAdmin, IPAuthorizedOfficer] else False
            )

    def test_get_allowed_amp_groups_audit(self):
        engagement = EngagementFactory()
        response = self.forced_auth_req(
            "get",
            self.url,
            user=UserFactory(
                realms__data=[UNICEFAuditFocalPoint.name],
                profile__organization=engagement.agreement.auditor_firm.organization
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_groups = sorted(
            GroupEditPermissionMixin.GROUPS_ALLOWED_MAP.get(UNICEFAuditFocalPoint.name, {}).get('audit', []))
        actual_groups = sorted([group['name'] for group in response.data['groups']])
        self.assertEqual(expected_groups, actual_groups)
        self.assertEqual(response.data['can_add_user'], True)

    def test_get_no_groups_allowed_empty(self):
        for user_group in [UNICEFUser, Auditor, PME, ThirdPartyMonitor]:
            response = self.forced_auth_req(
                "get",
                self.url,
                user=UserFactory(
                    realms__data=[user_group.name], profile__organization=self.organization
                )
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['groups'], [])
            self.assertEqual(response.data['can_add_user'], False)


class TestUserRealmView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        # clearing groups cache
        GroupWrapper.invalidate_instances()

        cls.organization = OrganizationFactory()
        cls.partner = PartnerFactory(organization=cls.organization)
        cls.user = UserFactory(realms__data=[], profile__organization=cls.organization)

        cls.ip_viewer = UserFactory(realms__data=[IPViewer.name], profile__organization=cls.organization)
        cls.ip_editor = UserFactory(realms__data=[IPEditor.name], profile__organization=cls.organization)
        cls.ip_admin = UserFactory(realms__data=[IPAdmin.name], profile__organization=cls.organization)
        cls.ip_auth_officer = UserFactory(realms__data=[IPAuthorizedOfficer.name], profile__organization=cls.organization)

        cls.partnership_manager = UserFactory(is_staff=True, realms__data=[UNICEF_USER, PartnershipManager.name])
        cls.audit_focal_point = AuditFocalPointUserFactory(is_staff=True)
        cls.pme = PMEUserFactory(is_staff=True)
        cls.unicef_user = UserFactory(is_staff=True)

    def make_request_list(self, auth_user, method='post', data=None):
        response = self.forced_auth_req(
            method,
            reverse("users_v3:realms-list"),
            user=auth_user,
            data=data,
        )
        return response

    def make_request_detail(self, auth_user, user_id, method='patch', data=None):
        response = self.forced_auth_req(
            method,
            reverse("users_v3:realms-detail", args=[user_id]),
            user=auth_user,
            data=data,
        )
        return response

    def test_get_list_forbidden(self):
        # self.user has no realm defined
        for auth_user in [self.user]:
            response = self.make_request_list(auth_user, method='get')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_list_filter_by_roles(self):
        data = {"roles": f"{IPEditor.as_group().pk},{IPViewer.as_group().pk}"}
        for auth_user in [self.ip_viewer, self.ip_editor, self.ip_admin,
                          self.ip_auth_officer]:
            response = self.make_request_list(auth_user, method='get', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 2, "Number of IP Viewers and Editors")

    def test_get_list_for_partner_users(self):
        # uses profile.organization = self.organization
        for auth_user in [self.ip_viewer, self.ip_editor, self.ip_admin,
                          self.ip_auth_officer]:
            with self.assertNumQueries(3):
                response = self.make_request_list(auth_user, method='get')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 4, "Number of users in realm")

    def test_get_list_for_unicef_users(self):
        for auth_user in [self.unicef_user, self.partnership_manager, self.audit_focal_point]:
            data = {
                "organization_id": self.organization.id,
                "organization_type": self.organization.relationship_types[0]
            }
            with self.assertNumQueries(4):
                response = self.make_request_list(auth_user, method='get', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 4)

    def test_get_empty_list_organization_not_found(self):
        data = {"organization_id": 12345}
        response = self.make_request_list(self.partnership_manager, method='get', data=data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_empty_list(self):
        # organization without a partner type
        data = {
            "organization_id": OrganizationFactory().pk,
            "organization_type": 'partner',
        }
        response = self.make_request_list(self.partnership_manager, method='get', data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

        # without organization_type query param
        data = {"organization_id": self.organization.id}
        response = self.make_request_list(self.partnership_manager, method='get', data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_post_forbidden(self):
        for auth_user in [self.ip_viewer, self.ip_editor]:
            self.assertEqual(self.user.realms.count(), 0)

            response = self.make_request_list(auth_user, data={})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # creating a unicef user from AMP is forbidden
        data = {
            "first_name": "First Name",
            "last_name": f"{auth_user.id} Last Name",
            "email": "test@unicef.org",
            "groups": [GroupFactory(name=IPViewer.name).pk],
        }
        response = self.make_request_list(auth_user, data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_new_partner_user(self):
        for auth_user, group in zip(
                [self.ip_admin, self.ip_auth_officer],
                [IPViewer, IPEditor]):
            email = f"{auth_user.id}_email@example.com"
            data = {
                "first_name": "First Name",
                "last_name": f"{auth_user.id} Last Name",
                "email": email,
                "phone_number": "+10999909999",
                "groups": [GroupFactory(name=group.name).pk],
            }
            response = self.make_request_list(auth_user, data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            staged_user = StagedUser.objects.get(user_json__email=email)
            self.assertEqual(staged_user.requester, auth_user)
            self.assertEqual(staged_user.request_state, StagedUser.PENDING)

    def test_post_new_auditor_user(self):
        self.assertFalse(self.audit_focal_point.is_superuser)
        self.assertTrue(self.audit_focal_point.is_staff)

        email = "auditor_email@example.com"
        data = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": email,
            "phone_number": "+10999909999",
            "groups": [GroupFactory(name=Auditor.name).pk],
            "organization": EngagementFactory().agreement.auditor_firm.organization.pk
        }
        response = self.make_request_list(self.audit_focal_point, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        staged_user = StagedUser.objects.get(user_json__email=email)
        self.assertEqual(staged_user.requester, self.audit_focal_point)
        self.assertEqual(staged_user.request_state, StagedUser.PENDING)

    def test_post_new_tpm_user(self):
        self.assertFalse(self.pme.is_superuser)
        self.assertTrue(self.pme.is_staff)

        email = "tpm_email@example.com"
        data = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": email,
            "phone_number": "+10999909999",
            "groups": [GroupFactory(name=ThirdPartyMonitor.name).pk],
            "organization": TPMPartnerFactory(countries=[connection.tenant]).organization.pk
        }
        response = self.make_request_list(self.pme, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        staged_user = StagedUser.objects.get(user_json__email=email)
        self.assertEqual(staged_user.requester, self.pme)
        self.assertEqual(staged_user.request_state, StagedUser.PENDING)

    def test_post_user_exists_201(self):
        for auth_user, group in zip(
                [self.ip_admin, self.ip_auth_officer],
                [IPViewer, IPEditor]):

            existing_user = UserFactory(email=f"{auth_user.pk}_email@example.com", realms__data=[],
                                        profile__organization=self.organization)
            self.assertEqual(existing_user.realms.count(), 0)

            data = {
                "first_name": "First Name",
                "last_name": f"{auth_user.id} Last Name",
                "email": existing_user.email,
                "job_title": "Dev",
                "groups": [GroupFactory(name=group.name).pk],
            }
            response = self.make_request_list(auth_user, data=data)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertFalse(StagedUser.objects.filter(user_json__email=existing_user.email).exists(), False)
            self.assertEqual(existing_user.realms.count(), 1)
            self.assertEqual(group.name, response.data['realms'][0]['group_name'])
            self.assertIn(group.as_group(), existing_user.groups)

    def test_post_partnership_manager_201(self):
        self.assertFalse(self.partnership_manager.is_superuser)
        self.assertTrue(self.partnership_manager.is_staff)

        group = GroupFactory(name=IPEditor.name)
        email = "new_email@example.com"
        data = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": email,
            "job_title": "Dev",
            "organization": self.organization.pk,
            "groups": [group.pk],
        }
        response = self.make_request_list(self.partnership_manager, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        staged_user = StagedUser.objects.get(user_json__email=email)
        self.assertEqual(staged_user.requester, self.partnership_manager)
        self.assertEqual(staged_user.request_state, StagedUser.PENDING)

    def test_patch_reactivate_groups(self):
        self.assertFalse(self.ip_admin.is_superuser)
        self.assertFalse(self.ip_admin.is_staff)

        self.assertEqual(self.user.realms.count(), 0)
        # create IPViewer and IPEditor realms
        data = {
            "user": self.user.id,
            "groups": [
                GroupFactory(name=IPViewer.name).pk,
                GroupFactory(name=IPEditor.name).pk
            ]
        }
        response = self.make_request_detail(self.ip_admin, self.user.id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for realm in response.data['realms']:
            self.assertTrue(realm['is_active'])
        self.assertEqual(len(response.data['realms']), 2)
        self.assertEqual(self.user.realms.filter(is_active=True).count(), 2)

        # deactivate IPViewer and IPEditor and activate IPAuthorizedOfficer
        data["groups"] = [GroupFactory(name=IPAuthorizedOfficer.name).pk]
        response = self.make_request_detail(self.ip_admin, self.user.id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.realms.count(), 3)
        self.assertEqual(self.user.realms.filter(is_active=True).count(), 1)

        # deactivate all groups
        data["groups"] = []
        response = self.make_request_detail(self.ip_admin, self.user.id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.realms.count(), 3)
        self.assertEqual(self.user.realms.filter(is_active=True).count(), 0)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.profile.organization)

        # reactivate IPViewer and IPEditor
        data["groups"] = [GroupFactory(name=IPViewer.name).pk, GroupFactory(name=IPEditor.name).pk]
        response = self.make_request_detail(self.ip_admin, self.user.id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.realms.filter(is_active=True).count(), 2)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_patch_partnership_manager_200(self):
        new_user = UserFactory(realms__data=[], profile__organization=self.organization)
        data = {
            "organization": self.organization.pk,
            "groups": [GroupFactory(name=IPViewer.name).pk, GroupFactory(name=IPEditor.name).pk],
        }
        response = self.make_request_detail(self.partnership_manager, new_user.id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for realm in response.data['realms']:
            self.assertTrue(realm['is_active'])
        self.assertEqual(len(response.data['realms']), 2)


class TestStagedUserViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        # clearing groups cache
        GroupWrapper.invalidate_instances()

        cls.organization = OrganizationFactory()
        cls.partner = PartnerFactory(organization=cls.organization)
        cls.user = UserFactory(realms__data=[], profile__organization=cls.organization)

        cls.ip_admin = UserFactory(realms__data=[IPAdmin.name], profile__organization=cls.organization)

        cls.user_reviewer = UserFactory(is_staff=True, realms__data=[UNICEF_USER, UserReviewer.name])
        cls.unicef_user = UserFactory(is_staff=True)

    def make_request_list(self, auth_user, method='post', data=None):
        response = self.forced_auth_req(
            method,
            reverse("users_v3:amp-staged-list"),
            user=auth_user,
            data=data,
        )
        return response

    def make_request_detail(self, auth_user, user_id, method='post', action='accept'):
        response = self.forced_auth_req(
            method,
            reverse(f"users_v3:amp-staged-{action}", args=[user_id]),
            user=auth_user,
        )
        return response

    def test_get_list(self):
        StagedUserFactory(user_json={
            "email": "test@test.com",
            "groups": [GroupFactory(name=IPViewer.name).pk],
            "username": "test@test.com",
            "last_name": "First Name",
            "first_name": "Last Name",
        })
        response = self.make_request_list(self.unicef_user, method='get')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_accept_forbidden(self):
        staged_user = StagedUserFactory(user_json={
            "email": "test@test.com",
            "groups": [GroupFactory(name=IPViewer.name).pk],
            "username": "test@test.com",
            "last_name": "First Name",
            "first_name": "Last Name",
        })
        response = self.make_request_detail(self.ip_admin, staged_user.pk, action='accept')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        staged_user.refresh_from_db()
        self.assertEqual(staged_user.request_state, StagedUser.PENDING)

    def test_accept(self):
        new_user_email = "test@test.com"
        staged_user = StagedUserFactory(
            user_json={
                "email": new_user_email,
                "groups": [GroupFactory(name=IPViewer.name).pk],
                "username": new_user_email,
                "last_name": "First Name",
                "first_name": "Last Name"
            },
            organization=self.organization,
            requester=self.ip_admin
        )
        response = self.make_request_detail(self.user_reviewer, staged_user.pk, action='accept')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        staged_user.refresh_from_db()
        self.assertEqual(staged_user.request_state, StagedUser.ACCEPTED)
        self.assertEqual(staged_user.reviewer, self.user_reviewer)

        self.assertTrue(User.objects.filter(email=new_user_email).exists())
        created_user = User.objects.get(email=new_user_email)
        self.assertEqual(created_user.realms.count(), 1)

    def test_decline_forbidden(self):
        staged_user = StagedUserFactory(
            user_json={
                "email": "test@test.com",
                "groups": [GroupFactory(name=IPViewer.name).pk],
                "username": "test@test.com",
                "last_name": "First Name",
                "first_name": "Last Name"
            },
            organization=self.organization)
        response = self.make_request_detail(self.unicef_user, staged_user.pk, action='decline')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        staged_user.refresh_from_db()
        self.assertEqual(staged_user.request_state, StagedUser.PENDING)

    def test_decline(self):
        staged_user = StagedUserFactory(
            user_json={
                "email": "test@test.com",
                "groups": [GroupFactory(name=IPViewer.name).pk],
                "username": "test@test.com",
                "last_name": "First Name",
                "first_name": "Last Name"
            },
            organization=self.organization)
        response = self.make_request_detail(self.user_reviewer, staged_user.pk, action='decline')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        staged_user.refresh_from_db()
        self.assertEqual(staged_user.request_state, StagedUser.DECLINED)
        self.assertEqual(staged_user.reviewer, self.user_reviewer)


class TestExternalUserAPIView(BaseTenantTestCase):
    fixtures = ['organizations']

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(realms__data=['PSEA Assessor'])
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.unicef_superuser = UserFactory(is_superuser=True)
        cls.auditor_user = AuditorUserFactory()
        cls.tpmpartner = SimpleTPMPartnerFactory()
        cls.tpmpartner_user = TPMUserFactory(
            tpm_partner=cls.tpmpartner,
        )

    def test_list(self):
        with self.assertNumQueries(2):
            response = self.forced_auth_req(
                'get',
                reverse("users_v3:external-list"),
                user=self.unicef_staff,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get(self):
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:external-detail", args=[self.user.pk]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.pk)

    def test_get_not_in_schema(self):
        user = UserFactory(realms__data=[])
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:external-detail", args=[user.pk]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post(self):
        email = "new@example.com"
        user_qs = get_user_model().objects.filter(email=email)
        self.assertFalse(user_qs.exists())
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": email,
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(user_qs.exists())
        user = user_qs.first()
        self.assertIn(self.tenant, user.profile.countries_available)
        self.assertEqual(self.tenant, user.profile.country_override)
        self.assertIn(Auditor.as_group(), user.groups)

    def test_post_exists(self):
        profile = ProfileFactory(user=UserFactory(realms__data=[]))
        self.assertNotIn(self.tenant, profile.countries_available)
        self.assertNotIn(Auditor.as_group(), profile.user.groups)
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": profile.user.email,
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile.refresh_from_db()
        self.assertIn(self.tenant, profile.countries_available)
        self.assertIn(Auditor.as_group(), profile.user.groups)

    def test_post_staff(self):
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": self.auditor_user.email,
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_post_unicef(self):
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": "test@unicef.org",
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_post_invalid_email(self):
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": "TEST@example.com",
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
