from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db import connection
from django.test import TestCase
from mock import Mock

from environment.helpers import tenant_flag_is_active, tenant_switch_is_active
from environment.tests.factories import (
    IssueCheckConfigFactory,
    TenantFlagFactory,
    FlagFactory,
    TenantSwitchFactory,
)
from EquiTrack.factories import CountryFactory


class IssueCheckConfigTest(TestCase):

    def test_str_method(self):
        issue_check_config = IssueCheckConfigFactory()
        expected = '{}: {}'.format(issue_check_config.check_id, issue_check_config.is_active)
        self.assertEqual(str(issue_check_config), expected)


class TenantFlagTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # create a base flag with 'everyone=False', so waffle will set the flag to False for everyone,
        # which makes it easier to test if our TenantFlag override is triggered or not.
        cls.flag = FlagFactory(everyone=False)
        cls.tenant_flag = TenantFlagFactory(flag=cls.flag)
        cls.country = CountryFactory()

    def setUp(self):
        self.request = Mock()
        # always assert that the base flag is False
        self.assertFalse(self.flag.is_active(self.request))
        self.request.tenant = self.country

    def test_str_method(self):
        self.assertEqual(str(self.tenant_flag), self.tenant_flag.flag.name)

    def test_request_has_no_tenant(self):
        "We should not raise Exception if request doesn't have a tenant."
        delattr(self.request, 'tenant')
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    def test_tenant_is_empty(self):
        "Return the base flag's value (False) if tenant is empty."
        self.request.tenant = None
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    def test_blank_countries(self):
        "Return the base flag's value (False) if TenantFlag has no countries."
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    def test_tenant_in_countries(self):
        "Return True if request tenant matches TenantFlag's countries."
        self.tenant_flag.countries.add(self.request.tenant)
        self.assertEqual(self.tenant_flag.is_active(self.request), True)

    def test_tenant_not_in_countries(self):
        "Return the base flag's value (False) if request.tenant is not in TenantFlag countries list."
        self.tenant_flag.countries.add(self.country)
        # Hacky hack: We can't create >1 Country object in tests. Instead change our tenant's PK so
        # that the code under test thinks that it is a different country.
        self.request.tenant.pk += 1
        self.assertEqual(self.tenant_flag.is_active(self.request), False)

    # test the tenant_flag_is_active helper function

    def test_is_active_function_good_flag(self):
        flag_active = tenant_flag_is_active(self.request, self.flag.name)
        # tenant not in countries, so this should return False
        self.assertFalse(flag_active)

    def test_is_active_function_nonexistent_flag(self):
        "Nonexistent flag should fall back to waffle's Flag implementation, which will return False."
        flag_active = tenant_flag_is_active(self.request, 'foo')
        self.assertFalse(flag_active)


class TenantSwitchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_switch = TenantSwitchFactory()
        connection.tenant = CountryFactory()

    def setUp(self):
        #assert the tenant switch is active but has no countries and returns false
        self.assertTrue(self.tenant_switch.active)
        self.assertEqual(0, self.tenant_switch.countries.count())
        self.assertFalse(self.tenant_switch.is_active())


    def test_str_method(self):
        self.assertEqual(str(self.tenant_switch), self.tenant_switch.name)

    def test_blank_countries(self):
        "Return the False if TenantSwitch has no countries."
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
        switch_active = tenant_switch_is_active(self.tenant_switch.name)
        # tenant not in countries, so this should return False
        self.assertFalse(switch_active)

    def test_is_active_function_switch_on(self):
        self.tenant_switch.countries.add(connection.tenant)
        # remove from cache after adding a country
        self.tenant_switch.flush()
        switch_active = tenant_switch_is_active(self.tenant_switch.name)
        # tenant in countries, so this should return True
        self.assertTrue(switch_active)

    def test_is_active_function_nonexistent_switch(self):
        "Nonexistent TenantSwitch should return False."
        switch_active = tenant_switch_is_active('foo')
        self.assertFalse(switch_active)
