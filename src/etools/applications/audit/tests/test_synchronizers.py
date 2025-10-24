import datetime
from decimal import Decimal
from unittest.mock import patch

from etools.applications.audit.models import FaceForm
from etools.applications.audit.synchronizers import FaceFormsSynchronizer
from etools.applications.audit.tests.factories import FaceFormFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory


class FaceFormsSynchronizerTestCase(BaseTenantTestCase):

    def setUp(self):
        self.partner = PartnerFactory(organization=OrganizationFactory(
            vendor_number="TEST_VENDOR_001",
            name="Test Partner"
        ))
        self.face_form = FaceFormFactory(
            face_number="FACE_001",
            partner=self.partner,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 12, 31),
            date_of_liquidation=datetime.date(2023, 12, 31),
            modality="Test Modality",
            currency="AFG",
            amount_local=Decimal("1200.00"),
            amount_usd=Decimal("1000.00")
        )
        self.valid_record = {
            "BUSINESS_AREA_CODE": "TEST_BA",
            "FACE_FORM_NUMBER": "FACE_002",
            "IMPLEMENTING_PARNTER_CODE": self.partner.vendor_number,
            "DOCUMENT_TYPE_DESC": "Cash",
            "CURRENCY": "AFG",
            "REPORTING_POSTING_DATE": "31-DEC-23",
            "REPORTING_START_DATE": "01-JAN-23",
            "REPORTING_END_DATE": "12-DEC-23",
            "HACT_FUNDINGS": {
                "TYPE_HACT_FUNDING": [
                    {
                        "OVERALL_AMOUNT": "1500.00",
                        "OVERALL_AMOUNT_USD": "1500.00"
                    }
                ]
            },
            "HACT_TRANSACTIONS": {
                "TYPE_HACT_TRANSACTION": {
                    "FACE_ENTERED": "0060 / 502200",
                    "FACE_ACCOUNTED": "0060 / 501096",
                    "FC_ITEM": "0100654833 / 001",
                    "AUTH_AMT": "2155914.00",
                    "AUTH_AMT_USD": "2155914.00"
                }
            }
        }

        self.synchronizer = FaceFormsSynchronizer(business_area_code=self.tenant.business_area_code)

    def test_init(self):
        sync = FaceFormsSynchronizer(business_area_code=self.tenant.business_area_code)
        self.assertEqual(sync.ENDPOINT, 'faceforms')
        self.assertEqual(sync.face_records, {})
        self.assertEqual(sync.funding_records, {})
        self.assertIsNotNone(sync.REVERSE_MAPPING)
        self.assertIsNotNone(sync.REVERSE_FACE_FORM_FIELDS)

    def test_set_kwargs(self):
        kwargs = self.synchronizer.set_kwargs(
            detail="test_detail",
            business_area_code=self.tenant.business_area_code
        )
        expected = {
            'detail': 'test_detail',
            'business_area_code': self.tenant.business_area_code,
            'businessareacode': self.tenant.business_area_code,
            'endpoint': 'faceforms'
        }
        self.assertEqual(kwargs, expected)

    def test_fill_required_keys(self):
        record = {"FACE_FORM_NUMBER": "TEST_001"}
        self.synchronizer._fill_required_keys(record)

        for key in self.synchronizer.REQUIRED_KEYS:
            self.assertIn(key, record)
            if key != "FACE_FORM_NUMBER":
                self.assertIsNone(record[key])

    def test_convert_records_list(self):
        records = [{"FACE_FORM_NUMBER": "TEST_001"}]
        result = self.synchronizer._convert_records(records)

        self.assertEqual(len(result), 1)
        self.assertIn("FACE_FORM_NUMBER", result[0])

    def test_filter_records_valid(self):
        valid_record = self.valid_record.copy()
        records = [valid_record]

        filtered = self.synchronizer._filter_records(records)
        self.assertEqual(len(filtered), 1)

    def test_filter_records_invalid(self):
        invalid_record = self.valid_record.copy()
        invalid_record["FACE_FORM_NUMBER"] = None

        records = [invalid_record]
        filtered = self.synchronizer._filter_records(records)
        self.assertEqual(len(filtered), 0)

    def test_get_value_for_field_date(self):
        date_str = "01-JAN-23"

        result = self.synchronizer.get_value_for_field('start_date', date_str)
        self.assertEqual(result, datetime.date(2023, 1, 1))

        result = self.synchronizer.get_value_for_field('end_date', date_str)
        self.assertEqual(result, datetime.date(2023, 1, 1))

    def test_get_value_for_field_partner(self):
        result = self.synchronizer.get_value_for_field('partner', self.partner.vendor_number)
        self.assertEqual(result, self.partner)

    def test_get_value_for_field_other(self):
        result = self.synchronizer.get_value_for_field('modality', 'Cash')
        self.assertEqual(result, 'Cash')

    def test_map_face_from_record_single_funding(self):
        record = self.valid_record.copy()
        result = self.synchronizer.map_face_from_record(record)

        self.assertEqual(result['face_number'], "FACE_002")
        self.assertEqual(result['amount_local'], Decimal("1500.00"))
        self.assertEqual(result['amount_usd'], Decimal("1500.00"))

    def test_map_face_from_record_multiple_funding(self):
        record = self.valid_record.copy()
        record["HACT_FUNDINGS"]["TYPE_HACT_FUNDING"] = [
            {"OVERALL_AMOUNT": "500.00", "OVERALL_AMOUNT_USD": "500.00"},
            {"OVERALL_AMOUNT": "1000.00", "OVERALL_AMOUNT_USD": "1000.00"}
        ]

        result = self.synchronizer.map_face_from_record(record)
        self.assertEqual(result['amount_local'], Decimal("1500.00"))
        self.assertEqual(result['amount_usd'], Decimal("1500.00"))

    def test_map_face_from_record_dict_funding(self):
        record = self.valid_record.copy()
        record["HACT_FUNDINGS"]["TYPE_HACT_FUNDING"] = {
            "OVERALL_AMOUNT": "1500.00",
            "OVERALL_AMOUNT_USD": "1500.00"
        }

        result = self.synchronizer.map_face_from_record(record)
        self.assertEqual(result['amount_local'], Decimal("1500.00"))
        self.assertEqual(result['amount_usd'], Decimal("1500.00"))

    def test_set_mapping(self):
        records = [self.valid_record]
        self.synchronizer.set_mapping(records)

        self.assertIn("FACE_002", self.synchronizer.face_records)
        self.assertEqual(self.synchronizer.face_records["FACE_002"]['face_number'], "FACE_002")

    def test_equal_fields_decimal(self):
        result = self.synchronizer.equal_fields('amount_local', Decimal("100.00"), Decimal("100.00"))
        self.assertTrue(result)

        result = self.synchronizer.equal_fields('amount_local', Decimal("100.00"), Decimal("200.00"))
        self.assertFalse(result)

    def test_equal_fields_other(self):
        result = self.synchronizer.equal_fields('modality', 'Cash', 'Cash')
        self.assertTrue(result)

        result = self.synchronizer.equal_fields('modality', 'Cash', 'Voucher')
        self.assertFalse(result)

    def test_update_obj_no_changes(self):
        new_record = {
            'face_number': self.face_form.face_number,
            'modality': self.face_form.modality,
            'amount_local': self.face_form.amount_local
        }

        result = self.synchronizer.update_obj(self.face_form, new_record)
        self.assertFalse(result)

    def test_update_obj_with_changes(self):
        new_record = {
            'face_number': self.face_form.face_number,
            'modality': 'New Modality',
            'amount_local': Decimal("2000.00")
        }

        result = self.synchronizer.update_obj(self.face_form, new_record)
        self.assertTrue(result)
        self.assertEqual(self.face_form.modality, 'New Modality')
        self.assertEqual(self.face_form.amount_local, 2000)

    def test_face_form_sync_create_new(self):
        records = [self.valid_record]
        self.synchronizer.set_mapping(records)

        updated, created = self.synchronizer.face_form_sync()

        self.assertEqual(updated, 0)
        self.assertEqual(created, 1)
        self.assertTrue(FaceForm.objects.filter(face_number="FACE_002").exists())

    def test_face_form_sync_update_existing(self):
        record = self.valid_record.copy()
        record["FACE_FORM_NUMBER"] = self.face_form.face_number
        record["DOCUMENT_TYPE_DESC"] = "Updated Modality"

        records = [record]
        self.synchronizer.set_mapping(records)

        updated, created = self.synchronizer.face_form_sync()

        self.assertEqual(updated, 1)
        self.assertEqual(created, 0)
        self.face_form.refresh_from_db()
        self.assertEqual(self.face_form.modality, "Updated Modality")

    def test_face_form_sync_no_partner(self):
        record = self.valid_record.copy()
        record["IMPLEMENTING_PARNTER_CODE"] = "NON_EXISTENT"

        records = [record]
        self.synchronizer.set_mapping(records)

        updated, created = self.synchronizer.face_form_sync()

        self.assertEqual(updated, 0)
        self.assertEqual(created, 0)

    def test_save_records(self):
        records = [self.valid_record]

        with patch.object(self.synchronizer, '_filter_records') as mock_filter, \
                patch.object(self.synchronizer, 'set_mapping'), \
                patch.object(self.synchronizer, 'face_form_sync', return_value=(1, 2)):
            mock_filter.return_value = records

            result = self.synchronizer._save_records(records)
            self.assertEqual(result, 3)  # 1 updated + 2 created

    def test_save_records_no_valid_records(self):
        records = [{"invalid": "record"}]

        with patch.object(self.synchronizer, '_filter_records') as mock_filter:
            mock_filter.return_value = []

            result = self.synchronizer._save_records(records)
            self.assertEqual(result, 0)

    def test_reverse_mapping_consistency(self):
        original_mapping = self.synchronizer.MAPPING
        reverse_mapping = self.synchronizer.REVERSE_MAPPING

        # Test that reverse mapping is the inverse of original mapping
        for key, value in original_mapping.items():
            self.assertEqual(reverse_mapping[value], key)

        # Test that all values in original mapping are keys in reverse mapping
        original_values = set(original_mapping.values())
        reverse_keys = set(reverse_mapping.keys())
        self.assertEqual(original_values, reverse_keys)
