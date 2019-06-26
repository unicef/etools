from django.core.exceptions import ValidationError
from django.test.testcases import SimpleTestCase

from etools.libraries.djangolib.validators import uppercase_forbidden_validator


class TestValidators(SimpleTestCase):

    def test_uppercase_forbidden_validator_unicef(self):
        uppercase_forbidden_validator('test-123@unicef.org')

    def test_uppercase_forbidden_validator_fail(self):
        with self.assertRaises(ValidationError) as ctx:
            uppercase_forbidden_validator('TEST-123@unicef.org')
            self.assertEqual('uppercase_forbidden', str(ctx.exception))
