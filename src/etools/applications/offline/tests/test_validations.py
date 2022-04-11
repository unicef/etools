from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.offline.errors import BadValueError, ValidationError, ValueTypeMismatch
from etools.applications.offline.validations.numbers import GreaterThanValidation, LessThanValidation
from etools.applications.offline.validations.text import MaxLengthTextValidation, RegexTextValidation


class TextBasedValidationMixin:
    def get_validation(self):
        raise NotImplementedError

    def test_none(self):
        with self.assertRaises(ValueTypeMismatch):
            self.get_validation().validate(None)

    def test_number(self):
        with self.assertRaises(ValueTypeMismatch):
            self.get_validation().validate(1)


class TestMaxLengthTextValidation(TextBasedValidationMixin, BaseTenantTestCase):
    def get_validation(self):
        return MaxLengthTextValidation(max_length=100)

    def test_valid_text(self):
        MaxLengthTextValidation(max_length=100).validate('1' * 100)

    def test_invalid_text(self):
        with self.assertRaises(ValidationError):
            MaxLengthTextValidation(max_length=100).validate('1' * 101)


class TestRegexTextValidation(TextBasedValidationMixin, BaseTenantTestCase):
    def get_validation(self):
        return RegexTextValidation(regex=r'\d{6}\w')

    def test_valid_text(self):
        self.get_validation().validate('123456a')

    def test_invalid_text(self):
        with self.assertRaises(BadValueError):
            self.get_validation().validate('123456')


class NumberBasedValidation:
    def get_validation(self):
        raise NotImplementedError

    def test_none(self):
        with self.assertRaises(ValueTypeMismatch):
            self.get_validation().validate(None)

    def test_text(self):
        with self.assertRaises(ValueTypeMismatch):
            self.get_validation().validate(None)


class TestLessThanValidation(NumberBasedValidation, BaseTenantTestCase):
    def get_validation(self):
        return LessThanValidation(threshold=42, allow_equality=False)

    def test_valid_number(self):
        self.get_validation().validate(41)

    def test_invalid_number(self):
        with self.assertRaises(BadValueError):
            self.get_validation().validate(42)


class TestLessThanOrEqualValidation(NumberBasedValidation, BaseTenantTestCase):
    def get_validation(self):
        return LessThanValidation(threshold=42, allow_equality=True)

    def test_valid_number(self):
        self.get_validation().validate(42)

    def test_invalid_number(self):
        with self.assertRaises(BadValueError):
            self.get_validation().validate(43)


class TestGreaterThanValidation(NumberBasedValidation, BaseTenantTestCase):
    def get_validation(self):
        return GreaterThanValidation(threshold=42, allow_equality=False)

    def test_valid_number(self):
        self.get_validation().validate(43)

    def test_invalid_number(self):
        with self.assertRaises(BadValueError):
            self.get_validation().validate(42)


class TestGreaterThanOrEqualValidation(NumberBasedValidation, BaseTenantTestCase):
    def get_validation(self):
        return GreaterThanValidation(threshold=42, allow_equality=True)

    def test_valid_number(self):
        self.get_validation().validate(42)

    def test_invalid_number(self):
        with self.assertRaises(BadValueError):
            self.get_validation().validate(41)
