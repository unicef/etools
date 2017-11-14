from __future__ import unicode_literals

from EquiTrack.factories import (
    ProfileFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from users import models


class TestWorkspaceCounter(TenantTestCase):
    def setUp(self):
        super(TestWorkspaceCounter, self).setUp()
        self.counter = models.WorkspaceCounter.objects.first()

    def test_unicode(self):
        self.assertEqual(unicode(self.counter), self.counter.workspace.name)

    def test_get_next_value_invalid_counter_type(self):
        with self.assertRaises(AttributeError):
            self.counter.get_next_value("wrong")

    def test_get_next_value(self):
        self.assertEqual(self.counter.travel_reference_number_counter, 1)
        self.counter.get_next_value("travel_reference_number_counter")
        counter_update = models.WorkspaceCounter.objects.get(
            pk=self.counter.pk
        )
        self.assertEqual(counter_update.travel_reference_number_counter, 2)


class TestOffice(TenantTestCase):
    def test_unicode(self):
        o = models.Office(name="office")
        self.assertEqual(unicode(o), "office")


class TestSection(TenantTestCase):
    def test_unicode(self):
        s = models.Section(name="section")
        self.assertEqual(unicode(s), "section")


class TestUserProfileModel(TenantTestCase):
    def setUp(self):
        super(TestUserProfileModel, self).setUp()
        self.user = UserFactory(
            email="user@example.com",
            first_name="First",
            last_name="Last",
        )

    def test_email(self):
        p = models.UserProfile(user=self.user)
        self.assertEqual(p.email(), "user@example.com")

    def test_first_name(self):
        p = models.UserProfile(user=self.user)
        self.assertEqual(p.first_name(), "First")

    def test_lat_name(self):
        p = models.UserProfile(user=self.user)
        self.assertEqual(p.last_name(), "Last")

    def test_custom_update_user_is_staff_no_group(self):
        profile = ProfileFactory()
        self.assertFalse(profile.user.is_staff)
        res = models.UserProfile.custom_update_user(profile.user, {}, None)
        self.assertTrue(res)
        profile_updated = models.UserProfile.objects.get(pk=profile.pk)
        self.assertTrue(profile_updated.user.is_staff)

    def test_custom_update_user_country_not_found(self):
        profile = ProfileFactory()
        res = models.UserProfile.custom_update_user(
            profile.user,
            {"businessAreaCode": "404"},
            None
        )
        self.assertFalse(res)

    def test_save_staff_id(self):
        profile = ProfileFactory()
        profile.staff_id = ""
        profile.save()
        self.assertIsNone(profile.staff_id)

    def test_save_vendor_number(self):
        profile = ProfileFactory()
        profile.vendor_number = ""
        profile.save()
        self.assertIsNone(profile.vendor_number)


class TestUserModel(TenantTestCase):

    def test_create_user(self):
        user = UserFactory(
            profile__job_title='Chief Tea Maker'
        )
        self.assertTrue(
            'Chief Tea Maker',
            user.profile.job_title
        )

    def test_conversion_to_string(self):
        '''Exercise converting instances to string.'''
        user = UserFactory(first_name='Pel\xe9', last_name='Arantes do Nascimento')
        self.assertEqual(unicode(user), 'Pel\xe9 Arantes do Nascimento')


class TestCreatePartnerUser(TenantTestCase):
    def test_created_false(self):
        user = models.User(email="new@example.com")
        models.create_partner_user(None, user, False)
        self.assertFalse(
            models.User.objects.filter(email="new@example.com").exists()
        )

    def test_not_created(self):
        user = UserFactory(email="new@example.com", username="new@example.com")
        models.create_partner_user(None, user, True)
        self.assertTrue(
            models.UserProfile.objects.filter(user=user).exists()
        )

    def test_create(self):
        user = models.User(
            email="new@example.com",
            first_name="First",
            last_name="Last",
        )
        models.create_partner_user(None, user, True)
        self.assertTrue(
            models.User.objects.filter(email="new@example.com").exists()
        )
        self.assertTrue(models.UserProfile.objects.filter(
            user__email="new@example.com"
        ).exists())


class TestDeletePartnerRelationship(TenantTestCase):
    def test_delete(self):
        profile = ProfileFactory()
        profile.partner_staff_member = profile.user.pk
        profile.save()
        models.delete_partner_relationship(None, profile.user)
        profile_updated = models.UserProfile.objects.get(pk=profile.pk)
        self.assertIsNone(profile_updated.partner_staff_member)
        user = models.User.objects.get(pk=profile.user.pk)
        self.assertFalse(user.is_active)

    def test_delete_exception(self):
        user = UserFactory()
        self.assertIsNone(models.delete_partner_relationship(None, user))
