import json
import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.test import RequestFactory, SimpleTestCase

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


class TestGetAllFieldNames(SimpleTestCase):
    def test_get_all_field_names(self):
        '''Exercise get_all_field_names() which is Django-provided code to replace Model._meta.get_all_field_names()'''
        class Useless:
            pass

        class Dummy(models.Model):
            '''Model to contain the many different types of fields I want to test.

            The list of fields in the model is not exhaustive, but it covers a variety of Django field types.
            '''
            # CHOICES should not be in the list of field names
            CHOICES = (('to be'), ('not to be'))

            # fields 1 - 9 inclusive should be in the list of field names
            field01 = models.CharField(max_length=50)
            field02 = models.IntegerField(primary_key=True)
            field03 = models.IntegerField(db_index=True)
            field04 = models.IntegerField(editable=False)
            field05 = models.IntegerField()
            field06 = models.DateField()
            field07 = models.TextField(blank=True)
            field08 = models.IntegerField(unique=True)
            field09 = models.IntegerField(default=42)
            # fields 10 and 11 should be in the list of field names, along with the automatically-created fields
            # 'field10_id' and 'field11_id'
            field10 = models.ForeignKey(Group)
            field11 = models.OneToOneField(Group)
            # field 12 should be in the list of field names, but it doesn't get a 'field12_id' because it's M2M
            field12 = models.ManyToManyField(Group)
            # field 13 shouldn't be in the list of field names. Generic FKs are excluded according to the Django doc.
            # https://docs.djangoproject.com/en/1.10/ref/models/meta/#migrating-from-the-old-api
            field13 = GenericForeignKey()
            # fields 14 and 15 shouldn't be in the list of field names because they're not Django fields.
            field14 = {}
            field15 = Useless()

        expected_field_names = ['field{:02}'.format(i + 1) for i in range(12)]
        expected_field_names += ['field10_id', 'field11_id']
        expected_field_names.sort()

        actual_field_names = sorted(utils.get_all_field_names(Dummy))

        self.assertEqual(expected_field_names, actual_field_names)

        # Bonus -- if we're still under Django < 1.10 where Model._meta.get_all_field_names() still exists,
        # ensure our function produces the same results as that one.
        if hasattr(Dummy._meta, 'get_all_field_names'):
            actual_field_names = sorted(Dummy._meta.get_all_field_names())
            self.assertEqual(expected_field_names, actual_field_names)


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
                'model': 'users.user',
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
