from __future__ import absolute_import, division, print_function, unicode_literals

from unittest import skip

from django.apps import apps
from django.contrib.contenttypes.management import update_contenttypes
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase

from mock import Mock
from rest_framework import serializers

from utils.writable_serializers.serializers import (
    WritableNestedChildSerializerMixin, WritableNestedParentSerializerMixin, DeletableSerializerMixin,)
from utils.writable_serializers.tests.models import Child1, Parent, Child2, GenericChild, Child3, CodedGenericChild


class BaseWritableSerializersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models. So we need to create it manually.
        with connection.schema_editor() as editor:
            for model in [Child1, Parent, Child2, GenericChild, Child3, CodedGenericChild]:
                editor.create_model(model)

        update_contenttypes(apps.get_app_config('writable_serializers'))


class WritableSerializerSingleTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableSerializerSingleTestCase, cls).setUpTestData()

        class Child1Serializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = Child1
                fields = ['id', 'field', 'field2']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            child1 = Child1Serializer(required=False, allow_null=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'child1']

        cls.ParentSerializer = ParentSerializer

    def setUp(self):
        self.parent = Parent.objects.create(field=0)
        self.child1 = Child1.objects.create(parent=self.parent, field=1)

    def test_create(self):
        serializer = self.ParentSerializer(data={
            'field': 100,
            'child1': {
                'field': 101,
            }
        })

        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        self.assertEqual(Child1.objects.get(parent=parent).field, 101)

    def test_update(self):
        serializer = self.ParentSerializer(self.parent, data={
            'field': 100,
            'child1': {
                'field': 101,
            }
        })

        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        self.assertEqual(Child1.objects.get(id=self.child1.id).field, 101)
        self.assertEqual(Child1.objects.get(id=self.child1.id).parent.id, self.parent.id)
        self.assertEqual(Child1.objects.get(id=self.child1.id).parent.id, parent.id)

    def test_partial_update(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'child1': {
                'field2': 102,
            }
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child1.objects.get(id=self.child1.id).field, 1)
        self.assertEqual(Child1.objects.get(id=self.child1.id).field2, 102)

    def test_create_through_update(self):
        parent = Parent.objects.create(field=0)

        serializer = self.ParentSerializer(parent, partial=True, data={
            'child1': {
                'field': 101,
            }
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child1.objects.get(parent=parent).field, 101)

    def test_nullable(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'child1': None,
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertFalse(Child1.objects.filter(parent=self.parent).exists())


class WritableSerializerManyTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableSerializerManyTestCase, cls).setUpTestData()

        class Child2Serializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = Child2
                fields = ['id', 'field', 'field2']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            children2 = Child2Serializer(many=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'children2']

        cls.ParentSerializer = ParentSerializer

    def setUp(self):
        self.parent = Parent.objects.create(field=0)
        self.children2 = [
            Child2.objects.create(parent=self.parent, field=1),
            Child2.objects.create(parent=self.parent, field=2),
        ]

    def test_create(self):
        serializer = self.ParentSerializer(data={
            'field': 100,
            'children2': [{
                'field': 101,
            }, {
                'field': 102,
            }]
        })

        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        self.assertEqual(Child2.objects.filter(parent=parent).count(), 2)
        self.assertTrue(Child2.objects.filter(parent=parent, field=101).exists())
        self.assertTrue(Child2.objects.filter(parent=parent, field=102).exists())

    def test_update(self):
        serializer = self.ParentSerializer(self.parent, data={
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

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 2)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 101)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 102)

    def test_partial_update(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children2': [{
                'id': self.children2[0].id,
                'field2': 101,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 2)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 1)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field2, 101)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 2)

    def test_create_through_update(self):
        parent = Parent.objects.create(field=0)

        serializer = self.ParentSerializer(parent, partial=True, data={
            'children2': [{
                'field': 101,
            }, {
                'field': 102,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child2.objects.filter(parent=parent).count(), 2)
        self.assertTrue(Child2.objects.filter(parent=parent, field=101).exists())
        self.assertTrue(Child2.objects.filter(parent=parent, field=102).exists())


class WritableSerializerForwardTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableSerializerForwardTestCase, cls).setUpTestData()

        class ParentSerializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = Parent
                fields = ['id', 'field']

        class Child1Serializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            parent = ParentSerializer()

            class Meta:
                model = Child1
                fields = ['id', 'field', 'parent']

        cls.Child1Serializer = Child1Serializer

    def setUp(self):
        self.parent = Parent.objects.create(field=0)
        self.child1 = Child1.objects.create(parent=self.parent, field=1)

    def test_create(self):
        serializer = self.Child1Serializer(data={
            'field': 101,
            'parent': {
                'field': 100,
            }
        })

        serializer.is_valid(raise_exception=True)
        child1 = serializer.save()

        self.assertEqual(Parent.objects.get(id=child1.parent_id).field, 100)

    def test_update(self):
        serializer = self.Child1Serializer(self.child1, data={
            'field': 101,
            'parent': {
                'field': 100,
            }
        })

        serializer.is_valid(raise_exception=True)
        child1 = serializer.save()

        self.assertEqual(Parent.objects.get(id=child1.parent_id).field, 100)
        self.assertEqual(Parent.objects.get(id=child1.parent_id).id, self.parent.id)
        self.assertEqual(Parent.objects.get(id=self.child1.parent_id).id, self.parent.id)


class WritableSerializerGenericTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableSerializerGenericTestCase, cls).setUpTestData()

        class GenericSerializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = GenericChild
                fields = ['id', 'field']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            generic_children = GenericSerializer(many=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'generic_children']

        cls.ParentSerializer = ParentSerializer

    def setUp(self):
        self.parent = Parent.objects.create(field=0)
        self.generic_children = [
            GenericChild.objects.create(obj=self.parent, field=1),
            GenericChild.objects.create(obj=self.parent, field=2),
        ]

    def test_create(self):
        serializer = self.ParentSerializer(data={
            'field': 100,
            'generic_children': [{
                'field': 101,
            }, {
                'field': 102,
            }]
        })

        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        parent_content_type = ContentType.objects.get_for_model(Parent)
        self.assertEqual(GenericChild.objects.filter(content_type=parent_content_type, object_id=parent.id).count(), 2)
        self.assertTrue(
            GenericChild.objects.filter(content_type=parent_content_type, object_id=parent.id, field=101).exists()
        )
        self.assertTrue(
            GenericChild.objects.filter(content_type=parent_content_type, object_id=parent.id, field=102).exists()
        )

    def test_update(self):
        serializer = self.ParentSerializer(self.parent, data={
            'field': 100,
            'generic_children': [{
                'id': self.generic_children[0].id,
                'field': 101,
            }, {
                'id': self.generic_children[1].id,
                'field': 102,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        parent_content_type = ContentType.objects.get_for_model(Parent)
        self.assertEqual(
            GenericChild.objects.filter(content_type=parent_content_type, object_id=self.parent.id).count(), 2
        )
        self.assertEqual(GenericChild.objects.get(id=self.generic_children[0].id).field, 101)
        self.assertEqual(GenericChild.objects.get(id=self.generic_children[1].id).field, 102)

    def test_create_through_update(self):
        parent = Parent.objects.create(field=0)

        serializer = self.ParentSerializer(parent, partial=True, data={
            'generic_children': [{
                'field': 101,
            }, {
                'field': 102,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        parent_content_type = ContentType.objects.get_for_model(Parent)
        self.assertEqual(
            GenericChild.objects.filter(content_type=parent_content_type, object_id=parent.id).count(), 2
        )
        self.assertTrue(
            GenericChild.objects.filter(content_type=parent_content_type, object_id=parent.id, field=101).exists()
        )
        self.assertTrue(
            GenericChild.objects.filter(content_type=parent_content_type, object_id=parent.id, field=102).exists()
        )


class WritableCodedGenericRelationTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableCodedGenericRelationTestCase, cls).setUpTestData()

        class CodedGenericSerializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = CodedGenericChild
                fields = ['id', 'field']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            coded1_generic_children = CodedGenericSerializer(many=True)
            coded2_generic_children = CodedGenericSerializer(many=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'coded1_generic_children', 'coded2_generic_children']

        cls.ParentSerializer = ParentSerializer

    def setUp(self):
        self.parent = Parent.objects.create(field=0)
        self.coded1_child = CodedGenericChild.objects.create(obj=self.parent, code='code1', field=1)
        self.coded2_child = CodedGenericChild.objects.create(obj=self.parent, code='code2', field=2)

    def test_representation(self):
        serializer = self.ParentSerializer(self.parent)
        self.assertDictContainsSubset({
            'coded1_generic_children': [{
                'id': self.coded1_child.id,
                'field': 1,
            }],
            'coded2_generic_children': [{
                'id': self.coded2_child.id,
                'field': 2,
            }],
        }, serializer.data)

    def test_creation(self):
        serializer = self.ParentSerializer(data={
            'field': 100,
            'coded1_generic_children': [{
                'field': 101,
            }, {
                'field': 102,
            }],
            'coded2_generic_children': [{
                'field': 103,
            }]
        })

        serializer.is_valid(raise_exception=True)
        parent = serializer.save()

        parent_content_type = ContentType.objects.get_for_model(Parent)
        self.assertSequenceEqual(
            CodedGenericChild.objects.filter(
                content_type=parent_content_type, object_id=parent.id, code='code1'
            ).values_list('field', flat=True),
            [101, 102]
        )
        self.assertSequenceEqual(
            CodedGenericChild.objects.filter(
                content_type=parent_content_type, object_id=parent.id, code='code2'
            ).values_list('field', flat=True),
            [103]
        )


class WritableSerializerRequiredTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableSerializerRequiredTestCase, cls).setUpTestData()

        class Child1Serializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = Child1
                fields = ['id', 'field', 'field2']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            child1 = Child1Serializer(required=False, allow_null=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'child1']

        cls.ParentSerializer = ParentSerializer

    def test_create_through_update(self):
        parent = Parent.objects.create(field=0)

        serializer = self.ParentSerializer(parent, partial=True, data={
            'child1': {
                'field2': 1,
            }
        })

        serializer.is_valid(raise_exception=True)
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'child1': {
                'field': ['This field is required.'],
            }
        }, errors)


class WritableSerializerUniqueTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableSerializerUniqueTestCase, cls).setUpTestData()

        class Child3Serializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = Child3
                fields = ['id', 'field', 'field2']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            children3 = Child3Serializer(many=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'children3']

        cls.ParentSerializer = ParentSerializer

    def setUp(self):
        self.parent = Parent.objects.create(field=0)
        self.child3 = Child3.objects.create(parent=self.parent, field=1, field2=2)

    def test_unique(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children3': [{
                'field': 101,
                'field2': 2,
            }]
        })

        serializer.is_valid(raise_exception=True)
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'children3': [{
                'field2': ['child3 with this field2 already exists.']
            }]
        }, errors)

    def test_unique_for_new(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children3': [{
                'field': 101,
                'field2': 3,
            }, {
                'field': 102,
                'field2': 3,
            }]
        })

        serializer.is_valid(raise_exception=True)
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'children3': [{
            }, {
                'field2': ['child3 with this field2 already exists.'],
            }]
        }, errors)

    # TODO: Fix this.
    @skip('Unique together validation is not working.')
    def test_unique_together(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children3': [{
                'field': 101,
                'field2': 3,
            }, {
                'field': 101,
                'field2': 4
            }]
        })

        serializer.is_valid(raise_exception=True)
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'children3': [{

            }, {
                ''
            }]
        }, errors)


class WritableListSerializerTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(WritableListSerializerTestCase, cls).setUpTestData()

        class Child2Serializer(WritableNestedChildSerializerMixin, serializers.ModelSerializer):
            class Meta(WritableNestedChildSerializerMixin.Meta):
                model = Child2
                fields = ['id', 'field']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            children2 = Child2Serializer(many=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'children2']

        cls.ParentSerializer = ParentSerializer

        cls.parent = Parent.objects.create(field=0)
        cls.children2 = [
            Child2.objects.create(parent=cls.parent, field=1),
            Child2.objects.create(parent=cls.parent, field=2),
        ]

    def test_update(self):
        serializer = self.ParentSerializer(self.parent, data={
            'field': 0,
            'children2': [{
                'id': self.children2[0].id,
                'field': 101,
            }, {
                'id': self.children2[1].id,
                'field': 102,
            }, {
                'field': 103,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 3)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 101)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 102)
        self.assertEqual(Child2.objects.filter(parent=self.parent).exclude(
            id__in=[self.children2[0].id, self.children2[1].id]).get().field, 103)

    def test_partial_update(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children2': [{
                'id': self.children2[1].id,
                'field': 102,
            }, {
                'field': 103,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 3)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 1)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 102)
        self.assertEqual(Child2.objects.filter(parent=self.parent).exclude(
            id__in=[self.children2[0].id, self.children2[1].id]).get().field, 103)

    def test_deleting_excess(self):
        serializer = self.ParentSerializer(self.parent, data={
            'field': 0,
            'children2': [{
                'id': self.children2[1].id,
                'field': 102,
            }, {
                'field': 103,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 2)
        self.assertFalse(Child2.objects.filter(id=self.children2[0].id).exists())
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 102)
        self.assertEqual(Child2.objects.filter(parent=self.parent).exclude(
            id__in=[self.children2[0].id, self.children2[1].id]).get().field, 103)

    def test_missed(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children2': [{
                'id': 123123,
                'field': 100,
            }]
        })

        serializer.is_valid(raise_exception=True)
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'children2': [
                {'id': ["Child2 with pk `123123` doesn't exists."]}
            ]
        }, errors)

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 2)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 1)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 2)

    def test_duplication(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children2': [{
                'id': self.children2[0].id,
                'field': 101,
            }, {
                'id': self.children2[0].id,
                'field': 102,
            }]
        })

        serializer.is_valid(raise_exception=True)
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'children2': [
                {},
                {'id': ["Duplication child2 with pk `{}`.".format(self.children2[0].id)]}
            ]
        }, errors)

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 2)
        self.assertEqual(Child2.objects.get(id=self.children2[0].id).field, 1)
        self.assertEqual(Child2.objects.get(id=self.children2[1].id).field, 2)

    def test_nesting_raises(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children2': [{
                'id': self.children2[0].id,
                'field': 101,
            }, {
                'id': self.children2[1].id,
                'field': 102,
            }]
        })
        serializer.fields['children2'].child.update = Mock(
            side_effect=serializers.ValidationError({'non_field_error': ['Some error.']}))

        serializer.is_valid(raise_exception=True)
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'children2': [{
                'non_field_error': ['Some error.']
            }, {
                'non_field_error': ['Some error.']
            }]
        }, errors)


class DeletableSerializerTestCase(BaseWritableSerializersTestCase):
    @classmethod
    def setUpTestData(cls):
        super(DeletableSerializerTestCase, cls).setUpTestData()

        class Child2Serializer(DeletableSerializerMixin, WritableNestedChildSerializerMixin,
                               serializers.ModelSerializer):
            class Meta(DeletableSerializerMixin.Meta, WritableNestedChildSerializerMixin.Meta):
                model = Child2
                fields = ['id', 'field']

        class ParentSerializer(WritableNestedParentSerializerMixin, serializers.ModelSerializer):
            children2 = Child2Serializer(many=True)

            class Meta:
                model = Parent
                fields = ['id', 'field', 'children2']

        cls.ParentSerializer = ParentSerializer

        cls.parent = Parent.objects.create(field=0)
        cls.children2 = [
            Child2.objects.create(parent=cls.parent, field=1),
            Child2.objects.create(parent=cls.parent, field=2),
        ]

    def test_deleting(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children2': [{
                'id': self.children2[0].id,
                '_delete': True,
            }, {
                'id': self.children2[1].id,
                'field': 102,
            }]
        })

        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertEqual(Child2.objects.filter(parent=self.parent).count(), 1)
        self.assertFalse(Child2.objects.filter(id=self.children2[0].id).exists())

        self.assertEqual(len(serializer.data['children2']), 1)
        self.assertEqual(serializer.data['children2'][0]['id'], self.children2[1].id)

    def test_deleting_on_create(self):
        serializer = self.ParentSerializer(self.parent, partial=True, data={
            'children2': [{
                'field': 103,
                '_delete': True,
            }]
        })

        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.is_valid(raise_exception=True)
            serializer.save()
        errors = cm.exception.detail

        self.assertDictContainsSubset({
            'children2': [{'_delete': ['You can\'t delete not exist object.']}]
        }, errors)
