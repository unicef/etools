from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import TestCase

from rest_framework import serializers

from utils.common.serializers.mixins import PkSerializerMixin
from utils.common.tests.models import Parent


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
