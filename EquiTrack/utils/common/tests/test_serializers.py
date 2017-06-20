from django.test import TestCase
from rest_framework import serializers

from .models import Parent
from ..serializers import PkSerializerMixin


class PKFieldSerializerTestCase(TestCase):
    def test_pk_field(self):
        class Serializer(PkSerializerMixin, serializers.ModelSerializer):
            class Meta:
                model = Parent
                fields = ['pk', 'field']

        serializer = Serializer()
        self.assertEqual(serializer.pk_field, serializer.fields['pk'])

    def test_id_field(self):
        class Serializer(PkSerializerMixin, serializers.ModelSerializer):
            class Meta:
                model = Parent
                fields = ['id', 'field']

        serializer = Serializer()
        self.assertEqual(serializer.pk_field, serializer.fields['id'])
