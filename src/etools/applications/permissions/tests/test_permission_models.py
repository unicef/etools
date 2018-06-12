from django.test import override_settings, TestCase

from etools.applications.permissions.models.models import BasePermission
from etools.applications.users.tests.factories import GroupFactory, UserFactory


@override_settings(SHARED_APPS=[
    'django.contrib.auth',
    'etools.applications.permissions.tests'
    'etools.applications.users',
], INSTALLED_APPS=[
    'django.contrib.auth',
    'etools.applications.permissions.tests',
    'etools.applications.users',
])
class BasePermissionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        group1 = GroupFactory(name='Group1')
        group2 = GroupFactory(name='Group2')

        cls.user1 = UserFactory(username='user1')
        cls.user2 = UserFactory(username='user2')
        cls.user3 = UserFactory(username='user3')

        cls.user1.groups = [group1]
        cls.user2.groups = [group2]
        cls.user3.groups = [group1, group2]

    def test_user_type_detection(self):
        class Permission(BasePermission):
            USER_TYPES = (
                ('Group1', 'Group1'),
                ('Group2', 'Group2'),
            )

            class Meta:
                abstract = True

        self.assertEqual(Permission._get_user_type(self.user1), 'Group1')
        self.assertEqual(Permission._get_user_type(self.user2), 'Group2')

    def test_user_type_priority(self):
        class Permission(BasePermission):
            USER_TYPES = (
                ('Group1', 'Group1'),
                ('Group2', 'Group2'),
            )

            class Meta:
                abstract = True

        self.assertEqual(Permission._get_user_type(self.user3), 'Group1')

        class Permission(BasePermission):
            USER_TYPES = (
                ('Group2', 'Group2'),
                ('Group1', 'Group1'),
            )

            class Meta:
                abstract = True

        self.assertEqual(Permission._get_user_type(self.user3), 'Group2')
