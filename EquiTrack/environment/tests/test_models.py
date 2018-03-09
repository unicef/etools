from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.apps import apps
from django.db import connection
from django.test import TestCase
from django.test.utils import override_settings
from mock import Mock

from environment.apps import EnvironmentConfig
from environment.helpers import tenant_flag_is_active, tenant_switch_is_active
from environment.tests.factories import (
    IssueCheckConfigFactory,
    TenantFlagFactory,
    TenantSwitchFactory,
)
from EquiTrack.factories import CountryFactory, UserFactory, GroupFactory


class IssueCheckConfigTest(TestCase):

    def test_str_method(self):
        issue_check_config = IssueCheckConfigFactory()
        expected = '{}: {}'.format(issue_check_config.check_id, issue_check_config.is_active)
        self.assertEqual(str(issue_check_config), expected)


class EnvironmentConfigTest(TestCase):
    def test_apps(self):
        self.assertEqual(apps.get_app_config('environment').name, EnvironmentConfig.name)


class TenantFlagTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant_flag = TenantFlagFactory(superusers=False)
        cls.country = CountryFactory()
        cls.user = UserFactory()

    def setUp(self):
        self.user.refresh_from_db()
        self.request = Mock()
        self.request.user = self.user
        self.request.tenant = self.country

    def tearDown(self):
        # flush the cache
        self.tenant_flag.flush()

    def test_str_method(self):
        self.assertEqual(str(self.tenant_flag), self.tenant_flag.name)

    def test_request_has_no_tenant(self):
        "We should not raise Exception if request doesn't have a tenant."
        delattr(self.request, 'tenant')
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    def test_tenant_is_empty(self):
        "Return False if tenant is empty."
        self.request.tenant = None
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    def test_blank_countries(self):
        "Return False if TenantFlag has no countries."
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    def test_tenant_in_countries(self):
        "Return True if request tenant matches TenantFlag's countries."
        self.tenant_flag.countries.add(self.request.tenant)
        # In tests, we have to manually flush the cache. When created through
        # the admin, the only way to change countries is to click the 'Save'
        # button, which flushes the cache
        self.tenant_flag.save()  # <- save is necessary to mimic the admin
        self.assertEqual(self.tenant_flag.is_active(self.request), True)

    def test_tenant_not_in_countries(self):
        "Return False if request.tenant is not in TenantFlag countries list."
        self.tenant_flag.countries.add(self.country)
        # Hacky hack: We can't create >1 Country object in tests. Instead change our tenant's PK so
        # that the code under test thinks that it is a different country.
        self.request.tenant.pk += 1
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    # test the tenant_flag_is_active helper function

    def test_is_active_function_inactive_flag(self):
        "Return False if tenant not in countries"
        flag_active = tenant_flag_is_active(self.request, self.tenant_flag.name)
        # tenant not in countries, so this should return False
        self.assertFalse(flag_active)

    def test_is_active_function_nonexistent_flag(self):
        "Return False if flag name doesn't exist"
        flag_active = tenant_flag_is_active(self.request, 'foo')
        self.assertFalse(flag_active)

    def test_is_active_function_cached(self):
        "Return True if tenant is in countries. Use cache for repeated calls."
        self.tenant_flag.countries.add(self.request.tenant)
        self.tenant_flag.save()  # <- save is necessary to mimic the admin
        with self.assertNumQueries(2):
            # 1 query for the flag, and 1 for the countries
            flag_active = tenant_flag_is_active(self.request, self.tenant_flag.name)
        self.assertTrue(flag_active)
        with self.assertNumQueries(0):
            # zero queries, since it's cached
            flag_active = tenant_flag_is_active(self.request, self.tenant_flag.name)
        self.assertTrue(flag_active)

    # tests to re-test all of the Waffle functionality we copy/pasted :(

    def test_user_set_is_cached(self):
        f = TenantFlagFactory()
        f.users.add(self.user)
        f.save()
        with self.assertNumQueries(2):
            self.assertTrue(f.is_active(self.request))
        with self.assertNumQueries(0):
            self.assertTrue(f.is_active(self.request))

    def test_empty_user_set_is_cached(self):
        f = TenantFlagFactory()
        with self.assertNumQueries(4):
            self.assertFalse(f.is_active(self.request))
        with self.assertNumQueries(1):
            # we still need to query the user's list of groups
            self.assertFalse(f.is_active(self.request))

    def test_group_set_is_cached(self):
        f = TenantFlagFactory()
        group = GroupFactory()
        f.groups.add(group)
        f.save()
        self.user.groups.add(group)
        with self.assertNumQueries(4):
            self.assertTrue(f.is_active(self.request))
        with self.assertNumQueries(1):
            # we still need to query the user's list of groups
            self.assertTrue(f.is_active(self.request))

    def test_authenticated_flag(self):
        f = TenantFlagFactory(authenticated=True)
        self.assertTrue(f.is_active(self.request))

    def test_staff_flag(self):
        f = TenantFlagFactory(staff=True)
        self.request.user.is_staff = True
        self.assertTrue(f.is_active(self.request))

    def test_superuser_flag(self):
        f = TenantFlagFactory(superusers=True)
        self.request.user.is_superuser = True
        self.assertTrue(f.is_active(self.request))

    def test_languages_flag_true(self):
        f = TenantFlagFactory(languages='foo,bar')
        self.request.LANGUAGE_CODE = 'foo'
        self.assertTrue(f.is_active(self.request))

    def test_languages_flag_false(self):
        f = TenantFlagFactory(languages='foo,bar')
        self.request.LANGUAGE_CODE = 'nope'
        self.assertFalse(f.is_active(self.request))

    @override_settings(WAFFLE_OVERRIDE=True)
    def test_override(self):
        f = TenantFlagFactory()
        self.request.GET = {f.name: '1'}
        self.assertTrue(f.is_active(self.request))

    @override_settings(WAFFLE_OVERRIDE=True)
    def test_override_not_this_flag(self):
        f = TenantFlagFactory()
        self.request.GET = {}
        self.assertFalse(f.is_active(self.request))

    @override_settings(WAFFLE_TEST_COOKIE='foo_%s')
    def test_testing_mode_request(self):
        f = TenantFlagFactory(testing=True)
        cookie_name = 'foo_%s' % f.name
        self.request.GET = {cookie_name: None}
        self.request.waffle_tests = {f.name: None}
        self.request.COOKIES = {cookie_name: None}
        self.assertFalse(f.is_active(self.request))

    @override_settings(WAFFLE_TEST_COOKIE='foo_%s')
    def test_testing_mode_cookie(self):
        f = TenantFlagFactory(testing=True)
        cookie_name = 'foo_%s' % f.name
        self.request.GET = {}
        self.request.COOKIES = {cookie_name: None}
        self.assertFalse(f.is_active(self.request))

    @override_settings(WAFFLE_TEST_COOKIE='foo_%s')
    def test_testing_mode_no_request_or_cookie(self):
        f = TenantFlagFactory(testing=True)
        self.request.GET = {}
        self.request.COOKIES = {}
        self.assertFalse(f.is_active(self.request))

    def test_percent_low(self):
        f = TenantFlagFactory(percent=0.1)
        self.request.waffles = {}
        self.request.COOKIES = {}
        # random, so we don't really care about the result, just that this path
        # gets covered on most runs
        self.assertFalse(f.is_active(self.request) is None)

    def test_percent_high(self):
        f = TenantFlagFactory(percent=99.9)
        self.request.waffles = {}
        self.request.COOKIES = {}
        # random, so we don't really care about the result, just that this path
        # gets covered on most runs
        self.assertFalse(f.is_active(self.request) is None)

    def test_percent_uses_waffles_preferentially(self):
        f = TenantFlagFactory(percent=0.1)
        self.request.waffles = {f.name: [True]}
        self.request.COOKIES = {}
        self.assertTrue(f.is_active(self.request))

    @override_settings(WAFFLE_COOKIE='foo_%s')
    def test_percent_uses_cookie_preferentially(self):
        f = TenantFlagFactory(percent=0.1)
        cookie_name = 'foo_%s' % f.name
        self.request.waffles = {}
        self.request.COOKIES = {cookie_name: 'True'}
        self.assertTrue(f.is_active(self.request))


class TenantSwitchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_switch = TenantSwitchFactory(active=True)
        connection.tenant = CountryFactory()

    def setUp(self):
        # assert that the tenant switch is 'active', to make it easier to make
        # sure that our country override is working
        self.assertTrue(self.tenant_switch.active)

    def tearDown(self):
        # flush the cache
        self.tenant_switch.flush()

    def test_str_method(self):
        self.assertEqual(str(self.tenant_switch), self.tenant_switch.name)

    def test_blank_countries(self):
        "Return False if TenantSwitch has no countries."
        self.assertEqual(0, self.tenant_switch.countries.count())
        self.assertFalse(self.tenant_switch.is_active())

    def test_tenant_in_countries(self):
        "Return True if connection tenant matches TenantSwitch's countries."
        self.tenant_switch.countries.add(connection.tenant)
        self.assertTrue(self.tenant_switch.is_active())

    def test_tenant_not_in_countries(self):
        "Return False if connection.tenant is not in TenantSwitch countries list."
        self.tenant_switch.countries.add(connection.tenant)
        connection.tenant = None
        self.assertFalse(self.tenant_switch.is_active())

    # test the tenant_switch_is_active helper function

    def test_is_active_function_switch_off(self):
        "Return False if tenant not in countries"
        switch_active = tenant_switch_is_active(self.tenant_switch.name)
        self.assertFalse(switch_active)

    def test_is_active_function_switch_on(self):
        self.tenant_switch.countries.add(connection.tenant)
        # In tests, we have to manually flush the cache. When created through
        # the admin, the only way to change countries is to click the 'Save'
        # button, which flushes the cache
        self.tenant_switch.save()  # <- save is necessary to mimic the admin
        switch_active = tenant_switch_is_active(self.tenant_switch.name)
        # tenant in countries, so this should return True
        self.assertTrue(switch_active)

    def test_is_active_function_nonexistent_switch(self):
        "Nonexistent TenantSwitch should return False."
        switch_active = tenant_switch_is_active('foo')
        self.assertFalse(switch_active)

    def test_is_active_function_is_cached(self):
        self.tenant_switch.countries.add(connection.tenant)
        self.tenant_switch.save()  # <- save is necessary to mimic the admin
        with self.assertNumQueries(2):
            # First time takes 2 queries (one to get switch, and one to get countries list)
            switch_active = tenant_switch_is_active(self.tenant_switch.name)
        self.assertTrue(switch_active)
        with self.assertNumQueries(0):
            # Second time, takes zero queries
            switch_active = tenant_switch_is_active(self.tenant_switch.name)
        self.assertTrue(switch_active)
