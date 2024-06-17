from typing import Dict, List, Set
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from unicef_attachments.models import Attachment

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.offline.errors import (
    BadValueError,
    MissingRequiredValueError,
    ValidationError,
    ValueTypeMismatch,
)
from etools.applications.offline.fields import (
    BooleanField,
    ChoiceField,
    FloatField,
    IntegerField,
    MixedUploadedRemoteFileField,
    RemoteFileField,
    TextField,
    UploadedFileField,
)
from etools.applications.offline.fields.base import SkipField, ValidatedStructure
from etools.applications.offline.fields.choices import LocalFlatOptions, LocalPairsOptions, RemoteOptions
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


class TestChoiceField(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.meta = Metadata()
        cls.meta.options['local_flat'] = LocalFlatOptions([0, 1])
        cls.meta.options['local_pairs'] = LocalPairsOptions(((0, 'Zero'), (1, 'One')))

        class ExampleRemoteOptions(RemoteOptions):
            def get_options(self) -> List[Dict]:
                return [{'value': 0, 'label': 'Zero'}, {'value': 1, 'label': 'One'}]

            def get_keys(self) -> Set:
                return set(c['value'] for c in self.get_options())

        cls.meta.options['remote'] = ExampleRemoteOptions('https://example.com')

    def test_options_key_required(self):
        with self.assertRaises(ImproperlyConfigured):
            ChoiceField('test')

    def test_choices_validation(self):
        for field in [
            ChoiceField('local_flat', options_key='local_flat'),
            ChoiceField('local_pairs', options_key='local_pairs'),
            ChoiceField('remote', options_key='remote'),
        ]:
            field.validate(0, self.meta)
            field.validate(1, self.meta)

            with self.assertRaises(BadValueError):
                field.validate(2, self.meta)

            # string representation is not the same, so we shouldn't allow those values
            with self.assertRaises(BadValueError):
                field.validate('1', self.meta)


class TestUploadedFileField(BaseTenantTestCase):
    def test_existing_attachment(self):
        attachment = AttachmentFactory()
        self.assertEqual(attachment, UploadedFileField('test').validate(attachment.id, Metadata()))

    def test_not_existing_attachment(self):
        with self.assertRaises(ValidationError):
            UploadedFileField('test').validate(-1, Metadata())


class TestRemoteFileField(BaseTenantTestCase):
    @patch('etools.applications.offline.fields.files.download_remote_attachment.delay')
    def test_process(self, download_mock):
        with self.captureOnCommitCallbacks(execute=True):
            attachment = RemoteFileField('test').validate('some-url', Metadata())
        self.assertIsInstance(attachment, Attachment)
        download_mock.assert_called()


class TestMixedUploadedRemoteFileField(BaseTenantTestCase):
    def test_existing_attachment(self):
        attachment = AttachmentFactory()
        self.assertEqual(attachment, MixedUploadedRemoteFileField('test').validate(attachment.id, Metadata()))

    def test_not_existing_attachment(self):
        with self.assertRaises(ValidationError):
            MixedUploadedRemoteFileField('test').validate(-1, Metadata())

    @patch('etools.applications.offline.fields.files.download_remote_attachment.delay')
    def test_process(self, download_mock):
        with self.captureOnCommitCallbacks(execute=True):
            attachment = MixedUploadedRemoteFileField('test').validate('http://some-url', Metadata())
        self.assertIsInstance(attachment, Attachment)
        download_mock.assert_called()
