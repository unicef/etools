from django.test import TestCase

from etools.applications.offline.errors import MissingRequiredValueError, ValueTypeMismatch
from etools.applications.offline.fields import BooleanField, FloatField, IntegerField, TextField
from etools.applications.offline.fields.base import SkipField, ValidatedStructure
from etools.applications.offline.metadata import Metadata


class TestValidatedStructure(TestCase):
    def test_required(self):
        with self.assertRaises(MissingRequiredValueError):
            ValidatedStructure('test').validate(None, Metadata())

        with self.assertRaises(SkipField):
            ValidatedStructure('test', required=False).validate(None, Metadata())

    def test_repeatable(self):
        with self.assertRaises(ValueTypeMismatch):
            ValidatedStructure('test', repeatable=True).validate('a', Metadata())

        self.assertEqual(ValidatedStructure('test', repeatable=True).validate(['a'], Metadata()), ['a'])


class TestTextField(TestCase):
    def test_integer_cast_to_text(self):
        self.assertEqual(TextField('test').validate(1, Metadata()), '1')

    def test_valid_string(self):
        self.assertEqual(TextField('test').validate('example value', Metadata()), 'example value')


class TestIntegerField(TestCase):
    def test_text(self):
        with self.assertRaises(ValueTypeMismatch):
            IntegerField('test').validate('a', Metadata())

        # if value can be interpreted as number, it should be
        self.assertEqual(IntegerField('test').validate('1', Metadata()), 1)

        # but int is unable to parse floats
        with self.assertRaises(ValueTypeMismatch):
            IntegerField('test').validate('1.3', Metadata())

    def test_integer(self):
        self.assertEqual(IntegerField('test').validate(1, Metadata()), 1)
        self.assertEqual(IntegerField('test').validate(0, Metadata()), 0)

    def test_float(self):
        self.assertEqual(IntegerField('test').validate(1.3, Metadata()), 1)


class TestFloatField(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.meta = Metadata()

    def test_text(self):
        with self.assertRaises(ValueTypeMismatch):
            FloatField('test').validate('a', Metadata())

        # if value can be interpreted as number, it should be
        self.assertEqual(FloatField('test').validate('1', Metadata()), 1)
        self.assertEqual(FloatField('test').validate('1.3', Metadata()), 1.3)

    def test_integer(self):
        self.assertEqual(FloatField('test').validate(1, Metadata()), 1)

    def test_float(self):
        self.assertEqual(FloatField('test').validate(1.3, Metadata()), 1.3)


class TestBooleanField(TestCase):
    def test_text(self):
        self.assertEqual(BooleanField('test').validate('a', Metadata()), False)

        # if value can be parsed, it should be
        for value in ['True', 'true', '1', 'yes']:
            self.assertEqual(BooleanField('test').validate(value, Metadata()), True)
        for value in ['False', 'false', '0', 'no']:
            self.assertEqual(BooleanField('test').validate(value, Metadata()), False)

    def test_number(self):
        self.assertEqual(BooleanField('test').validate(1, Metadata()), True)
        self.assertEqual(BooleanField('test').validate(0, Metadata()), False)

    def test_boolean(self):
        self.assertEqual(BooleanField('test').validate(True, Metadata()), True)
        self.assertEqual(BooleanField('test').validate(False, Metadata()), False)
