import datetime

from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.governments.synchronizers import EWPsSynchronizer, EWPSynchronizer
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import CountryProgrammeFactory, ResultFactory, ResultTypeFactory


class TestEWPSynchronizer(BaseTenantTestCase):

    @classmethod
    def setUp(cls):
        cls.country_programme = CountryProgrammeFactory(
            wbs='0060/A0/07',
            name='Country Programme'
        )

        cls.output = ResultFactory(
            wbs='0060/A0/07/885/006',
            name='Output 1',
            result_type=ResultTypeFactory(name=ResultType.OUTPUT)
        )

        cls.key_intervention = ResultFactory(
            wbs='0060/A0/07/885/006/001',
            name='Key Intervention 1',
            result_type=ResultTypeFactory(name=ResultType.ACTIVITY)
        )

        cls.location = LocationFactory(
            p_code='L0',
            name='Location 0',
            admin_level=0
        )

        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                name='Test Partner',
                vendor_number='VENDOR001'
            )
        )

        cls.sample_data = {
            "remote_cps": ['0060/A0/07'],
            "remote_outputs": [{
                "wbs": "0060/A0/07/885/006",
                "workplan": "WP/0060A007/000143/01"
            }],
            "remote_kis": [{
                "wbs": "0060/A0/07/885/006/001",
                "output": "0060/A0/07/885/006",
                "workplan": "WP/0060A007/000143/01"
            }],
            "remote_partners": ['VENDOR001'],
            "remote_locations": ['L0'],
            "remote_ewps": {
                "WP/0060A007/000143/01": {
                    "ewp_id": "152539",
                    "wbs": "WP/0060A007/000143/01",
                    "name": "Child Protection Annual Workplan 2025 CO",
                    "status": "Signed",
                    "cost_center_code": "0060B00000",
                    "cost_center_name": "Location Cost Center",
                    "category_type": "Section",
                    "plan_type": "Annual",
                    "country_programme": "0060/A0/07"
                }
            },
            "activities": {
                "0060/A0/07/885/006/001/WPA0001": {
                    "wbs": "0060/A0/07/885/006/001/WPA0001",
                    "wpa_id": "187033",
                    "start_date": datetime.date(2025, 1, 1),
                    "end_date": datetime.date(2025, 12, 31),
                    "title": "KI-ACO : STAFF COSTS",
                    "description": "KI WR 2024: Strengthen Birth Registration services...",
                    "total_budget": 2370684.0,
                    "locations": ['L0'],
                    "partners": ['VENDOR001'],
                    "ewp_key_intervention": "0060/A0/07/885/006/001",
                    "workplan": "WP/0060A007/000143/01"
                }
            }
        }

    def test_synchronizer_init(self):
        sync = EWPSynchronizer(self.sample_data)

        self.assertEqual(sync.cps['0060/A0/07'], self.country_programme)
        self.assertEqual(sync.outputs['0060/A0/07/885/006'], self.output)
        self.assertEqual(sync.kis['0060/A0/07/885/006/001'], self.key_intervention)
        self.assertEqual(sync.locations['L0'], self.location)
        self.assertEqual(sync.partners['VENDOR001'], self.partner)


class TestEWPsSynchronizer(BaseTenantTestCase):

    def test_convert_records(self):
        synchronizer = EWPsSynchronizer(business_area_code=self.tenant.business_area_code)

        sample_input = {
            'ROWSET': {
                'ROW': [{
                    'BUSINESS_AREA_CODE': self.tenant.business_area_code,
                    "BUSINESS_AREA_NAME": self.tenant.name,
                    'CP_WBS': '0060/A0/07',
                    'VISION_ACTIVITY_WBS': '0060/A0/07/885/006/001',
                    'WPA_GID': '0060/A0/07/885/006/001/WPA0001',
                    'WP_GID': 'WP/0060A007/000143/01',
                    'WP_NAME': 'Test Workplan',
                    'WP_STATUS': 'Signed',
                    'WPA_GEOLOCATIONS': {'GEOLOCATION': {'P_CODE': 'AF'}},
                    "WPA_ID": "191865",
                    "WPA_TITLE": "KI-ER 2024: SOCIAL AND BEHAVIOR CHANGE AND COMMUNICATION",
                    "WPA_DESCRIPTION": "KI-ER 2024: Social and behavior change and communication",
                    "WP_ID": "147813",
                    "WPA_START_DATE": "01-JAN-24",
                    "WPA_END_DATE": "31-DEC-24",
                    "TOTAL_BUDGET": None,
                    "WPA_IMPLEMENTING_PARTNERS": {
                        "IMPL_PARTNER": {
                            "IMPLEMENTING_PARTNER_CODE": "2500200677",
                            "IMPLEMENTING_PARTNER_NAME": "Test Partner"
                        },
                    },
                    "COST_CENTER_CODE": "0060H00000",
                    "COST_CENTER_NAME": "Jalalabad, Eastern",
                    "PLAN_CATEGORY_TYPE": "Section",
                    "PLAN_TYPE": "Annual",
                    "PLAN_AT_KI_LEVEL": "No",
                }]
            }
        }

        result = synchronizer._convert_records(sample_input)

        self.assertEqual(len(result), 7)
        self.assertIn('0060/A0/07', result['remote_cps'])
        self.assertEqual(result['remote_partners'], set())
        self.assertFalse(result['remote_locations'], set())

    def test_clean_records(self):
        synchronizer = EWPsSynchronizer(business_area_code=self.tenant.business_area_code)

        CountryProgrammeFactory(wbs='0060/A0/07', name='Test CP')

        sample_records = [{
            'BUSINESS_AREA_CODE': self.tenant.business_area_code,
            "BUSINESS_AREA_NAME": self.tenant.name,
            'CP_WBS': '0060/A0/07',
            'VISION_ACTIVITY_WBS': '0060/A0/07/885/006/001',
            'WPA_GID': '0060/A0/07/885/006/001/WPA0001',
            'WP_GID': 'WP/0060A007/000143/01',
            'WP_NAME': 'Test Workplan',
            'WP_STATUS': 'Signed',
            'WPA_GEOLOCATIONS': {'GEOLOCATION': {'P_CODE': 'AF'}},
            "WPA_ID": "191865",
            "WPA_TITLE": "KI-ER 2024: SOCIAL AND BEHAVIOR CHANGE AND COMMUNICATION",
            "WPA_DESCRIPTION": "KI-ER 2024: Social and behavior change and communication",
            "WP_ID": "147813",
            "WPA_START_DATE": "01-JAN-24",
            "WPA_END_DATE": "31-DEC-24",
            "TOTAL_BUDGET": None,
            "WPA_IMPLEMENTING_PARTNERS": {
                "IMPL_PARTNER": {
                    "IMPLEMENTING_PARTNER_CODE": "2500200677",
                    "IMPLEMENTING_PARTNER_NAME": "Test Partner"
                },
            },
            "COST_CENTER_CODE": "0060H00000",
            "COST_CENTER_NAME": "Jalalabad, Eastern",
            "PLAN_CATEGORY_TYPE": "Section",
            "PLAN_TYPE": "Annual",
            "PLAN_AT_KI_LEVEL": "No",
        }]

        result = synchronizer._clean_records(sample_records)

        self.assertIn('0060/A0/07', result['remote_cps'])
        self.assertEqual(len(result['remote_ewps']), 1)
        self.assertEqual(len(result['activities']), 1)
