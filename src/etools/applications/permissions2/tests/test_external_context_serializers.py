from django.db import connection
from django.test import TestCase

from rest_framework import serializers

from etools.applications.permissions2.models import Permission
from etools.applications.permissions2.tests.models import Child1, Parent
from etools.applications.utils.writable_serializers.serializers import WritableNestedSerializerMixin

from ..serializers import PermissionsBasedSerializerMixin


class Child1Serializer(PermissionsBasedSerializerMixin, WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = Child1
        fields = ['id', 'field1', 'field2']


class ParentSerializer(PermissionsBasedSerializerMixin, WritableNestedSerializerMixin, serializers.ModelSerializer):
    children1 = Child1Serializer(many=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = Parent
        fields = ['id', 'field1', 'field2', 'children1']


class SerializersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models. So we need to create it manually.
        with connection.schema_editor() as editor:
            editor.create_model(Parent)
            editor.create_model(Child1)

        cls.parent = Parent.objects.create(field1=1, field2=2)
        cls.children1 = [
            Child1.objects.create(parent=cls.parent, field1=3, field2=4),
            Child1.objects.create(parent=cls.parent, field1=5, field2=6),
        ]

        Permission.objects.bulk_create([
            Permission(permission='edit', target='permissions2.parent.field1'),
            Permission(permission='edit', target='permissions2.parent.children1'),
            Permission(permission='edit', target='permissions2.child1.field1'),
            Permission(permission='edit', target='permissions2.parent.field2', condition=['user.group="PME"']),
            Permission(permission='edit', target='permissions2.child1.field2', condition=['user.group="PME"']),
        ])

    def test_representation(self):
        serializer = ParentSerializer(self.parent)
        self.assertDictContainsSubset({
            'field1': 1,
            'children1': [{
                'id': self.children1[0].id,
                'field1': 3,
            }, {
                'id': self.children1[1].id,
                'field1': 5,
            }]
        }, serializer.data)

        serializer = ParentSerializer(self.parent, context={'permission_context': ['user.group="PME"']})
        self.assertDictContainsSubset({
            'field1': 1,
            'field2': 2,
            'children1': [{
                'id': self.children1[0].id,
                'field1': 3,
                'field2': 4,
            }, {
                'id': self.children1[1].id,
                'field1': 5,
                'field2': 6,
            }]
        }, serializer.data)

    def test_creation(self):
        serializer = ParentSerializer(data={
            'field1': 101,
            'field2': 102,
            'children1': [{
                'field1': 103,
                'field2': 104,
            }, {
                'field1': 105,
                'field2': 106,
            }]
        })
        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        self.assertEqual(parent.field1, 101)
        self.assertIsNone(parent.field2)
        child = parent.children1.all()[0]
        self.assertEqual(child.field1, 103)
        self.assertIsNone(child.field2)
        child = parent.children1.all()[1]
        self.assertEqual(child.field1, 105)
        self.assertIsNone(child.field2)

        serializer = ParentSerializer(data={
            'field1': 101,
            'field2': 102,
            'children1': [{
                'field1': 103,
                'field2': 104,
            }, {
                'field1': 105,
                'field2': 106,
            }]
        }, context={'permission_context': ['user.group="PME"']})
        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        self.assertEqual(parent.field1, 101)
        self.assertEqual(parent.field2, 102)
        child = parent.children1.all()[0]
        self.assertEqual(child.field1, 103)
        self.assertEqual(child.field2, 104)
        child = parent.children1.all()[1]
        self.assertEqual(child.field1, 105)
        self.assertEqual(child.field2, 106)

    def test_updating(self):
        serializer = ParentSerializer(self.parent, data={
            'field1': 101,
            'field2': 102,
            'children1': [{
                'id': self.children1[0].id,
                'field1': 103,
                'field2': 104,
            }, {
                'id': self.children1[1].id,
                'field1': 105,
                'field2': 106,
            }]
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Parent.objects.get(id=self.parent.id).field1, 101)
        self.assertEqual(Parent.objects.get(id=self.parent.id).field2, 2)
        self.assertEqual(Child1.objects.get(id=self.children1[0].id).field1, 103)
        self.assertEqual(Child1.objects.get(id=self.children1[0].id).field2, 4)
        self.assertEqual(Child1.objects.get(id=self.children1[1].id).field1, 105)
        self.assertEqual(Child1.objects.get(id=self.children1[1].id).field2, 6)

        serializer = ParentSerializer(self.parent, data={
            'field1': 201,
            'field2': 202,
            'children1': [{
                'id': self.children1[0].id,
                'field1': 203,
                'field2': 204,
            }, {
                'id': self.children1[1].id,
                'field1': 205,
                'field2': 206,
            }]
        }, context={'permission_context': ['user.group="PME"']})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Parent.objects.get(id=self.parent.id).field1, 201)
        self.assertEqual(Parent.objects.get(id=self.parent.id).field2, 202)
        self.assertEqual(Child1.objects.get(id=self.children1[0].id).field1, 203)
        self.assertEqual(Child1.objects.get(id=self.children1[0].id).field2, 204)
        self.assertEqual(Child1.objects.get(id=self.children1[1].id).field1, 205)
        self.assertEqual(Child1.objects.get(id=self.children1[1].id).field2, 206)
