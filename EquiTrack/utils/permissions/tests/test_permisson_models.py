from django.contrib.auth.models import User, Group
from django.test import TestCase, override_settings

from utils.permissions.models import BasePermission


@override_settings(SHARED_APPS=[
    'django.contrib.auth',
    'utils.permissions.tests'
], INSTALLED_APPS=[
    'django.contrib.auth',
    'utils.permissions.tests',
])
class BasePermissionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        group1 = Group.objects.create(name='Group1')
        group2 = Group.objects.create(name='Group2')

        cls.user1 = User.objects.create(username='user1')
        cls.user2 = User.objects.create(username='user2')
        cls.user3 = User.objects.create(username='user3')

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
