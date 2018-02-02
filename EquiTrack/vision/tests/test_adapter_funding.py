from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from decimal import Decimal
import json

from EquiTrack.factories import (
    FundsCommitmentHeaderFactory,
    FundsCommitmentItemFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase
from funds.models import (
    FundsCommitmentHeader,
    FundsCommitmentItem,
    FundsReservationHeader,
    FundsReservationItem,
)
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
        self.fund_item = FundsReservationItemFactory(
            fr_ref_number="123-987",
            line_item=self.data["LINE_ITEM"],
            wbs=self.data["WBS_ELEMENT"],
            grant_number=self.data["GRANT_NBR"],
            fund=self.data["FUND"],
            overall_amount=self.data["OVERALL_AMOUNT"],
            overall_amount_dc=self.data["OVERALL_AMOUNT_DC"],
            due_date=datetime.date(2015, 5, 18),
            line_item_text=self.data["FR_LINE_ITEM_TEXT"],
        )
        self.fund_header = FundsReservationHeaderFactory(
            vendor_code=self.data["VENDOR_CODE"],
            fr_number=self.data["FR_NUMBER"],
            document_date=datetime.date(2015, 1, 14),
            fr_type=self.data["FR_TYPE"],
            currency=self.data["CURRENCY"],
            document_text=self.data["FR_DOCUMENT_TEXT"],
            intervention_amt=self.data["CURRENT_FR_AMOUNT"],
            total_amt=self.data["FR_OVERALL_AMOUNT"],
            actual_amt=self.data["ACTUAL_CASH_TRANSFER"],
            outstanding_amt=self.data["OUTSTANDING_DCT"],
            start_date=datetime.date(2015, 1, 13),
            end_date=datetime.date(2015, 12, 20),
        )
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
        fields = ["start_date", "end_date", "document_date", "due_date"]
        for field in fields:
            response = self.adapter.get_value_for_field(field, "15-Jan-14")
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

    def test_update_object(self):
        """Check that if a value does not match object then return True"""
        self.fund_item.fr_ref_number = "321-123",
        record = self.adapter.map_line_item_record(self.data)
        del record["fr_number"]
        self.assertTrue(self.adapter.update_obj(self.fund_item, record))
        self.assertEqual(self.fund_item.fr_ref_number, "123-987")

    def test_update_object_no_change(self):
        """Check that if all values match object then return False"""
        record = self.adapter.map_line_item_record(self.data)
        del record["fr_number"]
        self.assertFalse(self.adapter.update_obj(self.fund_item, record))

    def test_header_sync_update(self):
        """Check that FundsReservationHeader record updated
        if values differ
        """
        self.fund_header.vendor_code = "Code321"
        self.fund_header.save()
        self.adapter.set_mapping([self.data])
        updated, to_create = self.adapter.header_sync()
        self.assertEqual(updated, 1)
        self.assertEqual(to_create, 0)
        fund_header_updated = FundsReservationHeader.objects.get(
            pk=self.fund_header.pk
        )
        self.assertEqual(
            fund_header_updated.vendor_code,
            self.data["VENDOR_CODE"]
        )

    def test_header_sync_create(self):
        """Check that FundsReservationHeader record created
        if fr_number does not exist
        """
        self.data["FR_NUMBER"] = "333"
        fund_qs = FundsReservationHeader.objects.filter(fr_number="333")
        self.assertFalse(fund_qs.exists())
        self.adapter.set_mapping([self.data])
        updated, to_create = self.adapter.header_sync()
        self.assertEqual(updated, 0)
        self.assertEqual(to_create, 1)
        self.assertTrue(fund_qs.exists())

    def test_li_sync_update(self):
        """Check that FundsReservationItem record updated
        if values differ
        """
        self.fund_item.overall_amount = "30.00"
        self.fund_item.save()
        self.adapter.set_mapping([self.data])
        updated, to_create = self.adapter.li_sync()
        self.assertEqual(updated, 1)
        self.assertEqual(to_create, 0)
        fund_item_updated = FundsReservationItem.objects.get(
            pk=self.fund_item.pk
        )
        self.assertEqual(
            fund_item_updated.overall_amount,
            Decimal(self.data["OVERALL_AMOUNT"])
        )

    def test_li_sync_create(self):
        """Check that FundsReservationItem record created
        if fr_ref_number does not exist
        """
        self.data["LINE_ITEM"] = "333"
        fund_qs = FundsReservationItem.objects.filter(
            fr_ref_number="123-333"
        )
        self.assertFalse(fund_qs.exists())
        self.adapter.set_mapping([self.data])
        self.adapter.map_header_objects([self.fund_header])
        updated, to_create = self.adapter.li_sync()
        self.assertEqual(updated, 0)
        self.assertEqual(to_create, 1)
        self.assertTrue(fund_qs.exists())

    def test_save_records(self):
        self.data["LINE_ITEM"] = "333"
        response = self.adapter._save_records(
            {"ROWSET": {"ROW": [self.data]}}
        )
        self.assertEqual(response, 1)


class TestFundCommitmentSynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.all()[0]

    def setUp(self):
        self.data = {
            "VENDOR_CODE": "C321",
            "FC_NUMBER": "123",
            "FC_DOC_DATE": "15-Jan-17",
            "FR_TYPE": "Type",
            "CURRENCY": "USD",
            "FC_DOCUMENT_TEXT": "Random text",
            "EXCHANGE_RATE": "1.5",
            "RESP_PERSON": "Resp Person",
            "LINE_ITEM": "987",
            "WBS_ELEMENT": "WBS",
            "GRANT_NBR": "456",
            "FUND": "Fund",
            "GL_ACCOUNT": "0405",
            "DUE_DATE": "05-May-17",
            "FR_NUMBER": "333",
            "COMMITMENT_AMOUNT_USD": "20.00",
            "COMMITMENT_AMOUNT_DC": "25.00",
            "AMOUNT_CHANGED": "5.00",
            "FC_LINE_ITEM_TEXT": "Line of text",
        }
        self.expected_header = {
            "vendor_code": "C321",
            "fc_number": "123",
            "document_date": datetime.date(2017, 1, 15),
            "fc_type": "Type",
            "currency": "USD",
            "document_text": "Random text",
            "exchange_rate": "1.5",
            "responsible_person": "Resp Person",
        }
        self.expected_line_item = {
            "line_item": "987",
            "wbs": "WBS",
            "grant_number": "456",
            "fc_number": "123",
            "fr_number": "333",
            "fc_ref_number": "123-987",
            "fund": "Fund",
            "due_date": datetime.date(2017, 5, 5),
            "commitment_amount": Decimal("20.00"),
            "commitment_amount_dc": Decimal("25.00"),
            "amount_changed": Decimal("5.00"),
            "line_item_text": "Line of text",
        }
        self.date_fields = ["document_date", "due_date"]
        self.decimal_fields = [
            "commitment_amount",
            "commitment_amount_dc",
            "amount_changed",
        ]
        self.fund_item = FundsCommitmentItemFactory(
            fc_ref_number="123-987",
            line_item=self.data["LINE_ITEM"],
            wbs=self.data["WBS_ELEMENT"],
            grant_number=self.data["GRANT_NBR"],
            fund=self.data["FUND"],
            gl_account=self.data["GL_ACCOUNT"],
            due_date=datetime.date(2017, 5, 5),
            fr_number=self.data["FR_NUMBER"],
            commitment_amount=self.data["COMMITMENT_AMOUNT_USD"],
            commitment_amount_dc=self.data["COMMITMENT_AMOUNT_DC"],
            amount_changed=self.data["AMOUNT_CHANGED"],
            line_item_text=self.data["FC_LINE_ITEM_TEXT"],
        )
        self.fund_header = FundsCommitmentHeaderFactory(
            vendor_code=self.data["VENDOR_CODE"],
            fc_number=self.data["FC_NUMBER"],
            document_date=datetime.date(2017, 1, 15),
            fc_type=self.data["FR_TYPE"],
            currency=self.data["CURRENCY"],
            document_text=self.data["FC_DOCUMENT_TEXT"],
            exchange_rate=self.data["EXCHANGE_RATE"],
            responsible_person=self.data["RESP_PERSON"],
        )
        self.adapter = adapter.FundCommitmentSynchronizer(self.country)

    def test_init(self):
        a = adapter.FundCommitmentSynchronizer(self.country)
        self.assertEqual(a.header_records, {})
        self.assertEqual(a.item_records, {})
        self.assertEqual(a.fc_headers, {})

    def test_convert_records(self):
        self.assertEqual(
            self.adapter._convert_records(json.dumps([self.data])),
            [self.data]
        )

    def test_filter_records_no_commitment_amount_usd(self):
        """If no commitment amount usd then ignore record"""
        self.data["COMMITMENT_AMOUNT_USD"] = ""
        records = {"ROWSET": {"ROW": [self.data]}}
        response = self.adapter._filter_records(records)
        self.assertEqual(response, [])

    def test_filter_records_no_fc_number(self):
        """If no fc number then ignore record"""
        self.data["FC_NUMBER"] = ""
        records = {"ROWSET": {"ROW": [self.data]}}
        response = self.adapter._filter_records(records)
        self.assertEqual(response, [])

    def test_filter_records(self):
        """If have both fc number and commitment amount usd then keep record"""
        records = {"ROWSET": {"ROW": [self.data]}}
        response = self.adapter._filter_records(records)
        self.assertEqual(response, [self.data])

    def test_get_value_for_field_dates(self):
        """If a set field (date) then convert to datetime date type"""
        for field in self.date_fields:
            response = self.adapter.get_value_for_field(field, "15-Jan-14")
            self.assertEqual(response, datetime.date(2014, 1, 15))

    def test_get_value_for_field_amount(self):
        """If a set field (amount) then strip commas"""
        for field in self.decimal_fields:
            response = self.adapter.get_value_for_field(field, "12,500")
            self.assertEqual(response, Decimal("12500"))

    def test_get_value_for_field(self):
        """If NOT a set field (date, or amount) then return value"""
        response = self.adapter.get_value_for_field("random", "val")
        self.assertEqual(response, "val")

    def test_get_fc_item_number(self):
        self.assertEqual(self.adapter.get_fc_item_number(self.data), "123-987")

    def test_map_header_from_record(self):
        response = self.adapter.map_header_from_record(self.data)
        self.assertEqual(response, self.expected_header)

    def test_map_line_item_record(self):
        response = self.adapter.map_line_item_record(self.data)
        self.assertEqual(response, self.expected_line_item)

    def test_set_mapping(self):
        self.adapter.set_mapping([self.data])
        self.assertEqual(
            self.adapter.header_records,
            {"123": self.expected_header}
        )
        self.assertEqual(
            self.adapter.item_records,
            {"123-987": self.expected_line_item}
        )

    def test_equal_fields_decimal(self):
        """If field is amt field then do comp_decimal comparison"""
        for field in self.decimal_fields:
            self.assertTrue(self.adapter.equal_fields(field, "20.00", "20.00"))
            self.assertFalse(self.adapter.equal_fields(field, "20.0", "20.1"))

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

    def test_update_object(self):
        """Check that if a value does not match object then return True"""
        self.fund_item.fc_ref_number = "321-123",
        record = self.adapter.map_line_item_record(self.data)
        del record["fc_number"]
        self.assertTrue(self.adapter.update_obj(self.fund_item, record))
        self.assertEqual(self.fund_item.fc_ref_number, "123-987")

    def test_update_object_no_change(self):
        """Check that if all values match object then return False"""
        record = self.adapter.map_line_item_record(self.data)
        del record["fc_number"]
        self.assertFalse(self.adapter.update_obj(self.fund_item, record))

    def test_header_sync(self):
        """Check that FundsCommitmentHeader record updated
        if values differ
        """
        self.fund_header.vendor_code = "Code321"
        self.fund_header.save()
        self.adapter.set_mapping([self.data])
        updated, to_create = self.adapter.header_sync()
        self.assertEqual(updated, 1)
        self.assertEqual(to_create, 0)
        fund_header_updated = FundsCommitmentHeader.objects.get(
            pk=self.fund_header.pk
        )
        self.assertEqual(
            fund_header_updated.vendor_code,
            self.data["VENDOR_CODE"]
        )

    def test_header_sync_create(self):
        """Check that FundsCommitmentHeader record created
        if fr_number does not exist
        """
        self.data["FC_NUMBER"] = "333"
        fund_qs = FundsCommitmentHeader.objects.filter(fc_number="333")
        self.assertFalse(fund_qs.exists())
        self.adapter.set_mapping([self.data])
        updated, to_create = self.adapter.header_sync()
        self.assertEqual(updated, 0)
        self.assertEqual(to_create, 1)
        self.assertTrue(fund_qs.exists())

    def test_li_sync_update(self):
        """Check that FundsCommitmentItem record updated
        if values differ
        """
        self.fund_item.commitment_amount = "30.00"
        self.fund_item.save()
        self.adapter.set_mapping([self.data])
        updated, to_create = self.adapter.li_sync()
        self.assertEqual(updated, 1)
        self.assertEqual(to_create, 0)
        fund_item_updated = FundsCommitmentItem.objects.get(
            pk=self.fund_item.pk
        )
        self.assertEqual(
            fund_item_updated.commitment_amount,
            Decimal(self.data["COMMITMENT_AMOUNT_USD"])
        )

    def test_li_sync_create(self):
        """Check that FundsCommitmentItem record created
        if fc_ref_number does not exist
        """
        self.data["LINE_ITEM"] = "333"
        fund_qs = FundsCommitmentItem.objects.filter(
            fc_ref_number="123-333"
        )
        self.assertFalse(fund_qs.exists())
        self.adapter.set_mapping([self.data])
        self.adapter.map_header_objects([self.fund_header])
        updated, to_create = self.adapter.li_sync()
        self.assertEqual(updated, 0)
        self.assertEqual(to_create, 1)
        self.assertTrue(fund_qs.exists())

    def test_save_records(self):
        self.data["LINE_ITEM"] = "333"
        response = self.adapter._save_records(
            {"ROWSET": {"ROW": [self.data]}}
        )
        self.assertEqual(response, 1)
