
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase


from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users import models
from etools.applications.users.tests.factories import (CountryFactory, OfficeFactory,
                                                       ProfileFactory, UserFactory,)


class TestWorkspaceCounter(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.counter = models.WorkspaceCounter.objects.first()

    def test_str(self):
        self.assertEqual(str(self.counter), self.counter.workspace.name)

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


class TestOffice(BaseTenantTestCase):
    def test_str(self):
        o = models.Office(name="office")
        self.assertEqual(str(o), "office")


class TestUserProfileModel(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
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

    def test_last_name(self):
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


class TestUserModel(BaseTenantTestCase):

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
        self.assertEqual(str(user), 'Pel\xe9 Arantes do Nascimento')


class TestStrUnicode(SimpleTestCase):
    '''Ensure calling str() on model instances returns the right text.'''

    def test_country(self):
        instance = CountryFactory.build(name='xyz')
        self.assertEqual(str(instance), u'xyz')

        instance = CountryFactory.build(name=u'Magyarorsz\xe1g')
        self.assertEqual(str(instance), u'Magyarorsz\xe1g')

    def test_workspace_counter(self):
        instance = models.WorkspaceCounter()
        instance.workspace = CountryFactory.build(name='xyz')
        self.assertEqual(str(instance), u'xyz')

        instance = models.WorkspaceCounter()
        instance.workspace = CountryFactory.build(name=u'Magyarorsz\xe1g')
        self.assertEqual(str(instance), u'Magyarorsz\xe1g')

    def test_office(self):
        instance = OfficeFactory.build(name='xyz')
        self.assertEqual(str(instance), u'xyz')

        instance = OfficeFactory.build(name=u'Magyarorsz\xe1g')
        self.assertEqual(str(instance), u'Magyarorsz\xe1g')

    def test_user_profile(self):
        UserModel = get_user_model()
        user = UserModel(first_name='Sviatoslav', last_name='')
        instance = models.UserProfile()
        instance.user = user
        self.assertEqual(str(instance), u'User profile for Sviatoslav')

        user = UserModel(first_name=u'Sventoslav\u016d')
        instance = models.UserProfile()
        instance.user = user
        self.assertEqual(str(instance), u'User profile for Sventoslav\u016d')
