import json
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.serializers.json import DjangoJSONEncoder
from django.test import RequestFactory, SimpleTestCase

import mock
from freezegun import freeze_time

from etools.applications.EquiTrack import utils
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory

PATH_SET_TENANT = "etools.applications.EquiTrack.utils.connection.set_tenant"


class TestUtils(SimpleTestCase):
    """
    Test utils function
    """

    @freeze_time("2013-05-26")
    def test_get_current_year(self):
        """test get current year function"""

        current_year = utils.get_current_year()
        self.assertEqual(current_year, 2013)

    @freeze_time("2013-05-26")
    def test_get_quarter_default(self):
        """test current quarter function"""
        quarter = utils.get_quarter()
        self.assertEqual(quarter, 'q2')

    def test_get_quarter(self):
        """test current quarter function"""
        quarter = utils.get_quarter(datetime(2016, 10, 1))
        self.assertEqual(quarter, 'q4')


class TestSetCountry(BaseTenantTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.mock_set = mock.Mock()
        self.country = self.user.profile.country

    def test_set_country(self):
        request = self.factory.get("/")
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override(self):
        """Ideally we would be setup a different country
        But having issues creating another country outside of current schema
        """
        self.user.profile.countries_available.add(self.country)
        request = self.factory.get("/?{}={}".format(
            settings.SCHEMA_OVERRIDE_PARAM,
            self.country.name
        ))
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override_shortcode(self):
        """Ideally we would be setup a different country
        But having issues creating another country outside of current schema
        """
        self.user.profile.countries_available.add(self.country)
        request = self.factory.get(
            "/?{}={}".format(
                settings.SCHEMA_OVERRIDE_PARAM,
                self.country.country_short_code
            )
        )
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override_invalid(self):
        request = self.factory.get("/?{}=Wrong".format(
            settings.SCHEMA_OVERRIDE_PARAM
        ))
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override_not_avialable(self):
        """Ideally we would be setup a different country
        But having issues creating another country outside of current schema
        """
        self.user.profile.countries_available.remove(self.country)
        request = self.factory.get("/?{}={}".format(
            settings.SCHEMA_OVERRIDE_PARAM,
            self.country.name
        ))
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)


class TestSerialization(BaseTenantTestCase):
    def setUp(self):
        user = get_user_model().objects.create(username='user001', email='fred@example.com', is_superuser=True)
        grp = Group.objects.create(name='Group 2')
        user.groups.add(grp)
        perm = Permission.objects.first()
        user.user_permissions.add(perm)
        self.user = user
        self.group = grp
        self.permission = perm

    def test_simple_instance(self):
        user = self.user
        result = utils.model_instance_to_dictionary(user)

        # Recreate how a datetime ends up embedded in a string in the JSON,
        # which is not quite isoformat().
        serialized_date_joined = json.loads(json.dumps(user.date_joined, cls=DjangoJSONEncoder))

        self.assertEqual(
            result,
            {
                'username': 'user001',
                'first_name': '',
                'last_name': '',
                'is_active': True,
                'is_superuser': True,
                'is_staff': False,
                'last_login': None,
                'groups': [self.group.id],
                'user_permissions': [self.permission.id],
                'pk': user.id,
                'model': 'auth.user',
                'password': '',
                'email': 'fred@example.com',
                'date_joined': serialized_date_joined,
            }
        )

    def test_make_dictionary_serializable(self):
        user = self.user
        with mock.patch('etools.applications.EquiTrack.utils.model_instance_to_dictionary') as mock_serialize_model:
            mock_serialize_model.return_value = {'exclamation': 'Hello, world!'}
            d = {
                'user': user,
                'i': 27,
                's': 'Foo'
            }
            result = utils.make_dictionary_serializable(d)
            self.assertEqual(
                result,
                {u'i': 27, u's': u'Foo', u'user': {u'exclamation': u'Hello, world!'}}
            )
