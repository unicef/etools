from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import connection
from django.test import TestCase

from rest_framework import serializers

from utils.common.serializers.fields import SeparatedReadWriteField
from utils.common.tests.models import Child1, Parent


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = ['id', 'field']


class Child1Serializer(serializers.ModelSerializer):
    parent = SeparatedReadWriteField(
        read_field=ParentSerializer(read_only=True),
    )

    class Meta:
        model = Child1
        fields = ['id', 'field', 'parent']


class SeparateReadWriteTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models. So we need to create it manually.
        with connection.schema_editor() as editor:
            editor.create_model(Parent)
            editor.create_model(Child1)

        cls.parent = Parent.objects.create(id=1, field=1)
        cls.child1 = Child1.objects.create(field=2, parent=cls.parent)

    def test_representation(self):
        serializer = Child1Serializer(self.child1)

        self.assertDictContainsSubset({
            'parent': {
                'id': 1,
                'field': 1,
            }
        }, serializer.data)

    def test_creation(self):
        serializer = Child1Serializer(data={
            'field': 3,
            'parent': 1,
        })
        serializer.is_valid(raise_exception=True)
        child1 = serializer.save()

        self.assertEqual(child1.parent, self.parent)
        self.assertDictContainsSubset({
            'parent': {
                'id': 1,
                'field': 1,
            }
        }, serializer.data)

    def test_validation(self):
        serializer = Child1Serializer(data={
            'field': 4,
            'parent': 123,
        })

        self.assertFalse(serializer.is_valid())
        self.assertDictContainsSubset({
            'parent': ['Invalid pk "123" - object does not exist.']
        }, serializer.errors)

    def test_serializers_tree(self):
        serializer = Child1Serializer(self.child1, context={'var1': 123})

        self.assertEqual(serializer.fields['parent'].read_field.source_attrs, serializer.fields['parent'].source_attrs)
        self.assertEqual(serializer.fields['parent'].write_field.source_attrs, serializer.fields['parent'].source_attrs)
        self.assertEqual(serializer.fields['parent'].write_field.root, serializer)
        self.assertEqual(serializer.fields['parent'].write_field.context, {'var1': 123})

    def test_field_building(self):
        class DefaultChild1Serializer(serializers.ModelSerializer):
            class Meta:
                model = Child1
                fields = ['id', 'field', 'parent']

        serializer1 = Child1Serializer(self.child1)
        serializer2 = DefaultChild1Serializer(self.child1)

        field1 = serializer1.fields['parent'].write_field
        field2 = serializer2.fields['parent']
        self.assertEqual(field1.__class__, field2.__class__)
        self.assertEqual(field1._args, field2._args)
        self.assertEqual(field1._kwargs, field2._kwargs)
