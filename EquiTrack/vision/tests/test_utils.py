from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from unittest import TestCase

from vision import utils


class TestWCFJSONDateAsDatetime(TestCase):
    def test_none(self):
        self.assertIsNone(utils.wcf_json_date_as_datetime(None))

    def test_datetime(self):
        date = "/Date(1361336400000)/"
        result = utils.wcf_json_date_as_datetime(date)
        self.assertEqual(result, datetime.datetime(2013, 2, 20, 5, 0))

    def test_datetime_positive_sign(self):
        date = "/Date(00000001+1000)/"
        result = utils.wcf_json_date_as_datetime(date)
        self.assertEqual(
            result,
            datetime.datetime(1970, 1, 1, 10, 0, 0, 1000)
        )

    def test_datetime_negative_sign(self):
        date = "/Date(00000001-1000)/"
        result = utils.wcf_json_date_as_datetime(date)
        self.assertEqual(
            result,
            datetime.datetime(1969, 12, 31, 14, 0, 0, 1000)
        )


class TestWCFJSONDateAsDate(TestCase):
    def test_none(self):
        self.assertIsNone(utils.wcf_json_date_as_date(None))

    def test_datetime(self):
        date = "/Date(1361336400000)/"
        result = utils.wcf_json_date_as_date(date)
        self.assertEqual(result, datetime.date(2013, 2, 20))

    def test_datetime_positive_sign(self):
        date = "/Date(00000001+1000)/"
        result = utils.wcf_json_date_as_date(date)
        self.assertEqual(
            result,
            datetime.date(1970, 1, 1)
        )

    def test_datetime_negative_sign(self):
        date = "/Date(00000001-1000)/"
        result = utils.wcf_json_date_as_date(date)
        self.assertEqual(
            result,
            datetime.date(1969, 12, 31)
        )


class TestCompDecimals(TestCase):
    def test_not_equal(self):
        self.assertFalse(utils.comp_decimals(0.2, 0.3))

    def test_equal(self):
        self.assertTrue(utils.comp_decimals(0.2, 0.2))
