from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json

from EquiTrack.tests.mixins import FastTenantTestCase
from users.models import Country
from vision.adapters import funding as adapter


class TestFundReservationsSynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.all()[0]

    def setUp(self):
        self.data = {
            "VENDOR_CODE": "Code123",
            "FR_NUMBER": "123",
            "FR_DOC_DATE": "14-Jan-15",
            "FR_TYPE": "Type",
            "CURRENCY": "USD",
            "FR_DOCUMENT_TEXT": "Random Text",
            "FR_START_DATE": "13-Jan-15",
            "FR_END_DATE": "20-Dec-15",
            "LINE_ITEM": "987",
            "WBS_ELEMENT": "WBS",
            "GRANT_NBR": "456",
            "FUND": "Fund",
            "OVERALL_AMOUNT": "20.00",
            "OVERALL_AMOUNT_DC": "5.00",
            "FR_LINE_ITEM_TEXT": "Line item text",
            "DUE_DATE": "18-May-15",
            "FR_OVERALL_AMOUNT": "15.00",
            "CURRENT_FR_AMOUNT": "17.00",
            "ACTUAL_CASH_TRANSFER": "18.00",
            "OUTSTANDING_DCT": "19.00",
        }
        self.expected_headers = {
            "vendor_code": "Code123",
            "fr_number": "123",
            "document_date": datetime.date(2015, 1, 14),
            "fr_type": "Type",
            "currency": "USD",
            "document_text": "Random Text",
            "start_date": datetime.date(2015, 1, 13),
            "end_date": datetime.date(2015, 12, 20),
            "total_amt": "15.00",
            "intervention_amt": "17.00",
            "actual_amt": "18.00",
            "outstanding_amt": "19.00",
        }
        self.expected_line_item = {
            "line_item": "987",
            "fr_number": "123",
            "wbs": "WBS",
            "grant_number": "456",
            "fund": "Fund",
            "overall_amount": "20.00",
            "overall_amount_dc": "5.00",
            "due_date": datetime.date(2015, 5, 18),
            "line_item_text": "Line item text",
            "fr_ref_number": "123-987"
        }
        self.adapter = adapter.FundReservationsSynchronizer(self.country)

    def test_init(self):
        a = adapter.FundReservationsSynchronizer(self.country)
        self.assertEqual(a.header_records, {})
        self.assertEqual(a.item_records, {})
        self.assertEqual(a.fr_headers, {})

    def test_convert_records(self):
        self.assertEqual(
            self.adapter._convert_records(json.dumps([self.data])),
            [self.data]
        )

    def test_filter_records_no_overall_amount(self):
        """If no overall amount then ignore record"""
        self.data["OVERALL_AMOUNT"] = ""
        records = {"ROWSET": {"ROW": [self.data]}}
        response = self.adapter._filter_records(records)
        self.assertEqual(response, [])

    def test_filter_records_no_fr_number(self):
        """If no fr number then ignore record"""
        self.data["FR_NUMBER"] = ""
        records = {"ROWSET": {"ROW": [self.data]}}
        response = self.adapter._filter_records(records)
        self.assertEqual(response, [])

    def test_filter_records(self):
        """If have both overall number and fr number then keep record"""
        records = {"ROWSET": {"ROW": [self.data]}}
        response = self.adapter._filter_records(records)
        self.assertEqual(response, [self.data])

    def test_get_value_for_field_date(self):
        """If a set field (date) then convert to datetime date type"""
        response = self.adapter.get_value_for_field("start_date", "15-Jan-14")
        self.assertEqual(response, datetime.date(2014, 1, 15))

    def test_get_value_for_field(self):
        """If NOT a set field (date) then return value"""
        response = self.adapter.get_value_for_field("random", "val")
        self.assertEqual(response, "val")

    def test_get_fr_item_number(self):
        response = self.adapter.get_fr_item_number(self.data)
        self.assertEqual(response, "123-987")

    def test_map_header_from_record(self):
        response = self.adapter.map_header_from_record(self.data)
        self.assertEqual(response, self.expected_headers)

    def test_map_line_item_record(self):
        response = self.adapter.map_line_item_record(self.data)
        self.assertEqual(response, self.expected_line_item)

    def test_set_mapping(self):
        self.assertEqual(self.adapter.header_records, {})
        self.assertEqual(self.adapter.item_records, {})
        self.adapter.set_mapping([self.data])
        self.assertEqual(
            self.adapter.header_records,
            {"123": self.expected_headers}
        )
        self.assertEqual(
            self.adapter.item_records,
            {"123-987": self.expected_line_item}
        )

    def test_equal_fields_decimal(self):
        """If field is amt field then do comp_decimal comparison"""
        self.assertTrue(
            self.adapter.equal_fields("total_amt", "20.00", "20.00")
        )
        self.assertFalse(
            self.adapter.equal_fields("total_amt", "20.00", "20.01")
        )

    def test_equal_fields_line_item(self):
        """If field is line item then convert obj field to str
        prior to comparison
        """
        self.assertTrue(self.adapter.equal_fields("line_item", 20, "20"))
        self.assertFalse(self.adapter.equal_fields("line_item", 21, "22"))

    def test_equal_fields(self):
        """If field is not special do normal comparison"""
        self.assertTrue(self.adapter.equal_fields("fr_number", "123", "123"))
        self.assertFalse(self.adapter.equal_fields("fr_number", "124", "123"))
