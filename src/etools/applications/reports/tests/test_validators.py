import json

from django import forms

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.reports import validators


class TestValueNumbers(BaseTenantTestCase):
    def test_empty_string(self):
        with self.assertRaises(forms.ValidationError):
            (validators.value_numbers(""))

    def test_json_valid_str(self):
        d = json.dumps({"v": "123.00", "d": "321,00"})
        self.assertIsNone(validators.value_numbers(d))

    def test_json_valid(self):
        d = json.dumps({"v": 123.00, "d": 321})
        self.assertIsNone(validators.value_numbers(d))

    def test_json_none_invalid(self):
        d = json.dumps({"v": None, "d": 321})
        with self.assertRaises(forms.ValidationError):
            validators.value_numbers(d)

    def test_json_invalid(self):
        d = json.dumps({"v": "123.00", "d": "$321,00"})
        with self.assertRaises(forms.ValidationError):
            validators.value_numbers(d)

    def test_valid_str(self):
        self.assertIsNone(
            validators.value_numbers({"v": "123.00", "d": "321,00"})
        )

    def test_valid(self):
        self.assertIsNone(
            validators.value_numbers({"v": 123.00, "d": 321})
        )

    def test_invalid(self):
        with self.assertRaises(forms.ValidationError):
            validators.value_numbers({"v": "$123.00", "d": "321,00"})


class TestValueNoneOrNumbers(BaseTenantTestCase):
    def test_empty_string(self):
        with self.assertRaises(forms.ValidationError):
            (validators.value_none_or_numbers(""))

    def test_json_valid_str(self):
        d = json.dumps({"v": "123.00", "d": "321,00"})
        self.assertIsNone(validators.value_none_or_numbers(d))

    def test_json_valid(self):
        d = json.dumps({"v": 123.00, "d": 321})
        self.assertIsNone(validators.value_none_or_numbers(d))

    def test_json_none_valid(self):
        d = json.dumps({"v": None, "d": 321})
        self.assertIsNone(validators.value_none_or_numbers(d))

    def test_json_invalid(self):
        d = json.dumps({"v": "123.00", "d": "$321,00"})
        with self.assertRaises(forms.ValidationError):
            validators.value_none_or_numbers(d)

    def test_valid_str(self):
        self.assertIsNone(
            validators.value_none_or_numbers({"v": "123.00", "d": "321,00"})
        )

    def test_valid(self):
        self.assertIsNone(
            validators.value_none_or_numbers({"v": 123.00, "d": 321})
        )

    def test_invalid(self):
        with self.assertRaises(forms.ValidationError):
            validators.value_none_or_numbers({"v": "$123.00", "d": "321,00"})
