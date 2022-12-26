import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse

from rest_framework import status

from etools.applications.action_points.models import PME
from etools.applications.audit.models import Auditor, UNICEFAuditFocalPoint, UNICEFUser
from etools.applications.audit.tests.factories import AuditFocalPointUserFactory, AuditorUserFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.tpm.models import ThirdPartyMonitor
from etools.applications.tpm.tests.factories import SimpleTPMPartnerFactory, TPMUserFactory
from etools.applications.users.mixins import GroupEditPermissionMixin
from etools.applications.users.models import (
    IPAdmin,
    IPAuthorizedOfficer,
    IPEditor,
    IPViewer,
    PartnershipManager,
    User,
    UserProfile,
)
from etools.applications.users.serializers_v3 import AP_ALLOWED_COUNTRIES
from etools.applications.users.tests.factories import GroupFactory, ProfileFactory, RealmFactory, UserFactory
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


class TestPartnerOrganizationListView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        # clearing groups cache
        GroupWrapper.invalidate_instances()

        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super().setUp()
        self.url = reverse('users_v3:partner-organizations-list', args=[self.tenant.id])

    def test_get_forbidden_403(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_200(self):
        partnership_manager = UserFactory(realms__data=[UNICEF_USER, PartnershipManager.name])
        # organization without a related tenant partner will be filtered out
        OrganizationFactory()

        # marked for deletion tenant Partner will be filtered out
        organization1 = OrganizationFactory()
        PartnerFactory(organization=organization1, deleted_flag=True)

        response = self.forced_auth_req(
            "get",
            self.url,
            user=partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        organization2 = OrganizationFactory()
        PartnerFactory(organization=organization2)
        # add a user with realm for organization2
        UserFactory(realms__data=['IP Viewer'], profile__organization=organization2)

        response = self.forced_auth_req(
            "get",
            self.url,
            user=partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], organization2.id)


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

    def test_not_admin(self):
        user = UserFactory()
        response = self.forced_auth_req(
            'get',
            self.url,
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_users_list(self):
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
            user=self.unicef_superuser
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)

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


class TestGroupPermissionsViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory()
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("users_v3:amp-group-permissions")

    def test_get_allowed_amp_groups(self):
        GroupFactory(name=Auditor.name)

        for user_group in [IPViewer, IPEditor, IPAuthorizedOfficer, IPAdmin,
                           PartnershipManager, UNICEFAuditFocalPoint]:
            response = self.forced_auth_req(
                "get",
                self.url,
                user=UserFactory(
                    realms__data=[user_group.name], profile__organization=self.organization
                )
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            expected_groups = sorted(GroupEditPermissionMixin.GROUPS_ALLOWED_MAP.get(user_group.name, []))
            actual_groups = sorted([group['name'] for group in response.data['groups']])
            self.assertEqual(expected_groups, actual_groups)
            self.assertEqual(
                response.data['can_add_user'],
                True if user_group in [IPAdmin, IPAuthorizedOfficer, PartnershipManager] else False
            )

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
        cls.user = UserFactory(realms__data=[], profile__organization=cls.organization)

        cls.ip_viewer = UserFactory(realms__data=[IPViewer.name], profile__organization=cls.organization)
        cls.ip_editor = UserFactory(realms__data=[IPEditor.name], profile__organization=cls.organization)
        cls.ip_admin = UserFactory(realms__data=[IPAdmin.name], profile__organization=cls.organization)
        cls.ip_auth_officer = UserFactory(realms__data=[IPAuthorizedOfficer.name], profile__organization=cls.organization)

        cls.partnership_manager = UserFactory(realms__data=[UNICEF_USER, PartnershipManager.name])
        cls.audit_focal_point = AuditFocalPointUserFactory()

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

    def test_get_forbidden_403(self):
        # self.user has no realm defined
        for auth_user in [self.user]:
            response = self.make_request_list(auth_user, method='get')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_200(self):
        # uses profile.organization = self.organization
        for auth_user in [self.ip_viewer, self.ip_editor, self.ip_admin,
                          self.ip_auth_officer]:
            response = self.make_request_list(auth_user, method='get')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 4, "Number of users in realm")
        # uses profile.organization = Unicef
        for auth_user in [self.partnership_manager, self.audit_focal_point]:
            response = self.make_request_list(auth_user, method='get')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 2, "Number of users in realm")

    def test_get_by_organization_id_200(self):
        data = {"organization_id": self.organization.id}
        response = self.make_request_list(self.partnership_manager, method='get', data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)

    def test_get_by_organization_id_404(self):
        data = {"organization_id": 12345}
        response = self.make_request_list(self.partnership_manager, method='get', data=data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_by_organization_id_empty_list(self):
        # organization without a related realm
        data = {"organization_id": OrganizationFactory().pk}
        response = self.make_request_list(self.partnership_manager, method='get', data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_post_forbidden_403(self):
        for auth_user, group in zip(
                [self.ip_viewer, self.ip_editor, self.audit_focal_point],
                [IPViewer, IPAdmin, Auditor, IPViewer]):
            self.assertEqual(self.user.realms.count(), 0)

            response = self.make_request_list(auth_user, data={})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.user.realms.count(), 0)

    def test_post_create_new_201(self):
        for auth_user, group in zip(
                [self.ip_admin, self.ip_auth_officer],
                [IPViewer, IPEditor]):
            email = f"{auth_user.id}_email@example.com"
            data = {
                "first_name": "First Name",
                "last_name": f"{auth_user.id} Last Name",
                "email": email,
                "groups": [GroupFactory(name=group.name).pk],
            }
            response = self.make_request_list(auth_user, data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            new_user = User.objects.get(email=email)
            self.assertEqual(new_user.realms.count(), 1)
            self.assertEqual(group.name, response.data['realms'][0]['group_name'])
            self.assertIn(group, new_user.groups)

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
            self.assertEqual(existing_user.realms.count(), 1)
            self.assertEqual(group.name, response.data['realms'][0]['group_name'])
            self.assertIn(group.as_group(), existing_user.groups)

    def test_post_partnership_manager_201(self):
        group = GroupFactory(name=IPEditor.name)
        realm = RealmFactory(
            country=connection.tenant,
            organization=OrganizationFactory(),
            group=Auditor.as_group())
        email = "new_email@example.com"
        data = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": email,
            "job_title": "Dev",
            "organization": realm.organization.pk,
            "groups": [group.pk],
        }
        response = self.make_request_list(self.partnership_manager, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(email=email)
        self.assertEqual(new_user.realms.count(), 1)
        self.assertEqual(group.name, response.data['realms'][0]['group_name'])
        self.assertIn(group, new_user.groups)

    def test_patch_reactivate_groups(self):
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

        # deactivate IPViewer and IPEditor
        data["groups"] = [GroupFactory(name=IPAuthorizedOfficer.name).pk]
        response = self.make_request_detail(self.ip_admin, self.user.id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.realms.count(), 3)
        self.assertEqual(self.user.realms.filter(is_active=True).count(), 1)

        # reactivate IPViewer and IPEditor and deactivate IPAuthorizedOfficer
        data["groups"] = [GroupFactory(name=IPViewer.name).pk, GroupFactory(name=IPEditor.name).pk]
        response = self.make_request_detail(self.ip_admin, self.user.id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.realms.filter(is_active=True).count(), 2)

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
