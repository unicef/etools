from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import connection
from django.test import TestCase

from rest_framework import serializers

from firms.factories import UserFactory
from firms.serializers import BaseStaffMemberSerializer
from firms.tests.models import StaffMember


class StaffMemberSerializer(BaseStaffMemberSerializer):
    class Meta(BaseStaffMemberSerializer.Meta):
        model = StaffMember


class SerializerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models by adding migrations package. So we need to create it manually.
        with connection.schema_editor() as editor:
            editor.create_model(StaffMember)

        user = UserFactory()
        cls.staff_member = StaffMember.objects.create(user=user)

    def test_representation(self):
        serializer = StaffMemberSerializer(self.staff_member)
        self.assertDictContainsSubset({
            'id': self.staff_member.id,
            'user': {
                'first_name': self.staff_member.user.first_name,
                'last_name': self.staff_member.user.last_name,
                'email': self.staff_member.user.email,
                'is_active': self.staff_member.user.is_active,
                'profile': {
                    'job_title': self.staff_member.user.profile.job_title,
                    'phone_number': self.staff_member.user.profile.phone_number,
                },
            },
        }, serializer.data)

    def test_creation(self):
        serializer = StaffMemberSerializer(data={
            'user': {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@test.com',
                'profile': {
                    'job_title': 'Tester',
                    'phone_number': '123456789',
                }
            }
        })
        serializer.is_valid(raise_exception=True)
        staff_member = serializer.save()

        self.assertEqual(staff_member.user.email, 'test@test.com')
        self.assertEqual(staff_member.user.profile.phone_number, '123456789')

    def test_updating(self):
        serializer = StaffMemberSerializer(self.staff_member, partial=True, data={
            'user': {
                'first_name': 'Test2',
                'profile': {
                    'phone_number': '987654321',
                }
            }
        })
        serializer.is_valid(raise_exception=True)
        staff_member = serializer.save()

        self.assertEqual(staff_member.user.id, self.staff_member.user.id)
        self.assertEqual(staff_member.user.first_name, 'Test2')
        self.assertEqual(staff_member.user.profile.id, self.staff_member.user.profile.id)
        self.assertEqual(staff_member.user.profile.phone_number, '987654321')

    def test_unique(self):
        serializer = StaffMemberSerializer(data={
            'user': {
                'first_name': 'Test',
                'last_name': 'User',
                'email': self.staff_member.user.email,
                'profile': {
                }
            }
        })
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.is_valid(raise_exception=True)
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'user': {
                'email': ['This field must be unique.'],
            }
        }, errors)
