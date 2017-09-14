import base64

from rest_framework import serializers

from EquiTrack.tests.mixins import FastTenantTestCase
from ..serializers_fields import Base64FileField


class TestBase64FileField(FastTenantTestCase):
    def setUp(self):
        self.test_file_content = 'these are the file contents!'

    def test_valid(self):
        valid_base64_file = 'data:text/plain;base64,{}'.format(base64.b64encode(self.test_file_content))
        self.assertIsNotNone(Base64FileField().to_internal_value(valid_base64_file))

    def test_invalid(self):
        with self.assertRaises(serializers.ValidationError):
            Base64FileField().to_internal_value(42)

    def test_corrupted(self):
        corrupted_base64_file = 'data;base64,{}'.format(base64.b64encode(self.test_file_content))
        with self.assertRaises(serializers.ValidationError):
            Base64FileField().to_internal_value(corrupted_base64_file)
