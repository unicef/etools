from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.test import TestCase

from rest_framework import serializers

from utils.permissions.serializers import PermissionsBasedSerializerMixin
from utils.permissions.tests.models import Child2, Parent, Permission
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class PermissionsBasedSerializerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        group1 = Group.objects.create(name='Group1')
        group2 = Group.objects.create(name='Group2')

        cls.user1 = User.objects.create(username='user1')
        cls.user2 = User.objects.create(username='user2')

        cls.user1.groups = [group1]
        cls.user2.groups = [group2]

        Permission.objects.bulk_create([
            Permission(user_type='Group1', permission='edit', target='parent.field'),
            Permission(user_type='Group1', permission='edit', target='parent.children2'),
            Permission(user_type='Group1', permission='edit', target='child2.field'),
            Permission(user_type='Group1', permission='view', target='child2.field2'),

            Permission(user_type='Group2', permission='view', target='parent.field'),
            Permission(user_type='Group2', permission='view', target='parent.children2'),
            Permission(user_type='Group2', permission='edit', target='child2.field2'),
        ])

        class Child2Serializer(PermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                               serializers.ModelSerializer):
            class Meta(PermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
                model = Child2
                fields = ['id', 'field']
                permission_class = Permission

        class ParentSerializer(PermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                               serializers.ModelSerializer):
            children2 = Child2Serializer(many=True)

            class Meta(PermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
                model = Parent
                fields = ['id', 'field', 'children2']
                permission_class = Permission

        cls.ParentSerializer = ParentSerializer

    def setUp(self):
        self.parent = Parent.objects.create(field=0)
        self.children2 = [
            Child2.objects.create(parent=self.parent, field=1),
            Child2.objects.create(parent=self.parent, field=2),
        ]

    def test_representation(self):
        serializer = self.ParentSerializer(self.parent, context={'user': self.user1})
        self.assertDictContainsSubset({
            'field': 0,
            'children2': [{
                'id': self.children2[0].id,
                'field': 1,
            }, {
                'id': self.children2[1].id,
                'field': 2,
            }]
        }, serializer.data)

        serializer = self.ParentSerializer(self.parent, context={'user': self.user2})
        self.assertDictContainsSubset({
            'field': 0,
            'children2': [{
                'id': self.children2[0].id,
            }, {
                'id': self.children2[1].id,
            }]
        }, serializer.data)

    def test_creation(self):
        serializer = self.ParentSerializer(context={'user': self.user1}, data={
            'field': 100,
            'children2': [{
                'field': 101,
            }, {
                'field': 102,
            }]
        })
        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        self.assertEqual(Parent.objects.get(id=parent.id).field, 100)
        self.assertEqual(Child2.objects.get(parent=parent, field=101).field, 101)
        self.assertEqual(Child2.objects.get(parent=parent, field=102).field, 102)

        serializer = self.ParentSerializer(context={'user': self.user2}, data={
            'field': 100,
            'children2': [{
                'field': 101,
            }, {
                'field': 102,
            }]
        })
        serializer.is_valid(raise_exception=True)
        with self.assertRaises(IntegrityError) as cm:
            serializer.save()
        self.assertIn('null value in column "field" violates not-null constraint', str(cm.exception))

    def test_updating(self):
        serializer = self.ParentSerializer(self.parent, context={'user': self.user1}, data={
            'field': 100,
            'children2': [{
                'id': self.children2[0].id,
                'field': 101,
            }, {
                'id': self.children2[1].id,
                'field': 102,
            }]
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Parent.objects.get(id=self.parent.id).field, 100)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 101)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 102)

        serializer = self.ParentSerializer(self.parent, context={'user': self.user2}, data={
            'field': 200,
            'children2': [{
                'id': self.children2[0].id,
                'field': 201,
            }, {
                'id': self.children2[1].id,
                'field': 202,
            }]
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Parent.objects.get(id=self.parent.id).field, 100)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 101)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 102)
