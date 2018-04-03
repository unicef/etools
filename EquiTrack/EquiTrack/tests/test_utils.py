# Python imports
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import datetime

import mock
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.serializers.json import DjangoJSONEncoder
from django.test import SimpleTestCase
from freezegun import freeze_time

from EquiTrack.tests.cases import BaseTenantTestCase
from EquiTrack.utils import get_current_year, get_quarter, model_instance_to_dictionary, make_dictionary_serializable


class TestUtils(SimpleTestCase):
    """
    Test utils function
    """

    @freeze_time("2013-05-26")
    def test_get_current_year(self):
        """test get current year function"""

        current_year = get_current_year()
        self.assertEqual(current_year, 2013)

    @freeze_time("2013-05-26")
    def test_get_quarter_default(self):

        """test current quarter function"""
        quarter = get_quarter()
        self.assertEqual(quarter, 'q2')

    def test_get_quarter(self):
        """test current quarter function"""
        quarter = get_quarter(datetime(2016, 10, 1))
        self.assertEqual(quarter, 'q4')


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
        result = model_instance_to_dictionary(user)

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
        with mock.patch('EquiTrack.utils.model_instance_to_dictionary') as mock_serialize_model:
            mock_serialize_model.return_value = {'exclamation': 'Hello, world!'}
            d = {
                'user': user,
                'i': 27,
                's': 'Foo'
            }
            result = make_dictionary_serializable(d)
            self.assertEqual(
                result,
                {u'i': 27, u's': u'Foo', u'user': {u'exclamation': u'Hello, world!'}}
            )
