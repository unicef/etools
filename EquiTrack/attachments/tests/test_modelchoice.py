from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.metadata import SimpleMetadata

from attachments.metadata import ModelChoiceFieldMixin
from attachments.models import FileType
from attachments.serializers_fields import FileTypeModelChoiceField
from attachments.tests.factories import FileTypeFactory
from EquiTrack.tests.mixins import FastTenantTestCase


class TestSerializer(serializers.Serializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='code1'))


class TestMetadata(ModelChoiceFieldMixin, SimpleMetadata):
    pass


class TestModelChoiceFileField(FastTenantTestCase):
    def setUp(self):
        self.code1_obj = FileTypeFactory(code='code1')
        self.code2_obj = FileTypeFactory(code='code2')

    def test_valid_serializer(self):
        valid_serializer = TestSerializer(data={'file_type': self.code1_obj.pk})
        self.assertTrue(valid_serializer.is_valid())

    def test_invalid_serializer(self):
        invalid_serializer = TestSerializer(data={'file_type': self.code2_obj.pk})
        self.assertFalse(invalid_serializer.is_valid())
        self.assertIn('file_type', invalid_serializer.errors)
        self.assertIn(
            _('Invalid option "{pk_value}" - option does not available.').format(pk_value=self.code2_obj.pk),
            invalid_serializer.errors['file_type']
        )

    def test_metadata(self):
        file_type_choices = map(
            lambda x: x['value'],
            TestMetadata().get_serializer_info(TestSerializer())['file_type']['choices']
        )
        self.assertIn(self.code1_obj.pk, file_type_choices)
        self.assertNotIn(self.code2_obj.pk, file_type_choices)
