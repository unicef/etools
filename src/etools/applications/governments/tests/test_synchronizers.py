import datetime
from copy import deepcopy

from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.governments.models import EWPActivity, EWPKeyIntervention, EWPOutput, GovernmentEWP
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
            p_code='LO',
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
            "remote_locations": ['LO'],
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
                    "locations": ['LO'],
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
        self.assertEqual(sync.locations['LO'], self.location)
        self.assertEqual(sync.partners['VENDOR001'], self.partner)
        # no existing data for the below
        self.assertEqual(sync.workplans, {})
        self.assertEqual(sync.ewp_outputs, {})
        self.assertEqual(sync.ewp_key_interventions, {})
        self.assertEqual(sync.activities, {})

    def test_update_workplans(self):
        sync = EWPSynchronizer(self.sample_data)

        total_data, total_updated, total_new = sync.update_workplans()

        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(total_new, 1)

        workplan = GovernmentEWP.objects.get(wbs='WP/0060A007/000143/01')
        self.assertEqual(workplan.name, 'Child Protection Annual Workplan 2025 CO')
        self.assertEqual(workplan.country_programme, self.country_programme)

        # Second run with same data - should detect no changes
        sample_copy = deepcopy(self.sample_data)

        sync = EWPSynchronizer(sample_copy)
        total_data, total_updated, total_new = sync.update_workplans()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(total_new, 0)

        # Test with modified data
        self.sample_data['remote_ewps']['WP/0060A007/000143/01']['name'] = 'Updated Name'

        sync = EWPSynchronizer(self.sample_data)
        total_data, total_updated, total_new = sync.update_workplans()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 1)
        self.assertEqual(total_new, 0)

        workplan.refresh_from_db()
        self.assertEqual(workplan.name, 'Updated Name')

    def test_update_ewp_outputs(self):
        sync = EWPSynchronizer(self.sample_data)

        # Need workplan first
        sync.update_workplans()

        total_data, total_updated, total_new = sync.update_ewp_outputs()

        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(total_new, 1)

        output = EWPOutput.objects.get(
            cp_output=self.output,
            workplan__wbs='WP/0060A007/000143/01'
        )
        self.assertEqual(output.cp_output, self.output)

    def test_update_kis(self):
        sync = EWPSynchronizer(self.sample_data)

        sync.update_workplans()
        sync.update_ewp_outputs()

        total_data, total_updated, total_new = sync.update_kis()

        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(total_new, 1)

        ki = EWPKeyIntervention.objects.get(
            cp_key_intervention=self.key_intervention,
            ewp_output__cp_output=self.output
        )
        self.assertEqual(ki.cp_key_intervention, self.key_intervention)

    def test_update_activities(self):
        sync = EWPSynchronizer(self.sample_data)

        # Need all prerequisite data
        sync.update_workplans()
        sync.update_ewp_outputs()
        sync.update_kis()

        total_data, total_updated, total_new = sync.update_activities()

        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(total_new, 1)

        activity = EWPActivity.objects.get(wbs='0060/A0/07/885/006/001/WPA0001')
        self.assertEqual(activity.title, 'KI-ACO : STAFF COSTS')
        self.assertEqual(activity.locations.first(), self.location)
        self.assertEqual(activity.partners.first(), self.partner)

    def test_full_update(self):
        sync = EWPSynchronizer(self.sample_data)
        result = sync.update()

        self.assertEqual(result['total_records'], 4)  # 1 workplan, 1 output, 1 KI, 1 activity
        self.assertEqual(result['processed'], 4)  # All should be new

        # Verify all objects were created
        self.assertEqual(GovernmentEWP.objects.count(), 1)
        self.assertEqual(EWPOutput.objects.count(), 1)
        self.assertEqual(EWPKeyIntervention.objects.count(), 1)
        self.assertEqual(EWPActivity.objects.count(), 1)


class TestEWPsSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUp(cls):
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                name='Test Partner',
                vendor_number='VENDOR001'
            )
        )
        cls.sample_input = {
            'ROWSET': {
                'ROW': [{
                    'BUSINESS_AREA_CODE': cls.tenant.business_area_code,
                    "BUSINESS_AREA_NAME": cls.tenant.name,
                    'CP_WBS': '0060/A0/07',
                    'VISION_ACTIVITY_WBS': '0060/A0/07/885/006/001',
                    'WPA_GID': '0060/A0/07/885/006/001/WPA0001',
                    'WP_GID': 'WP/0060A007/000143/01',
                    'WP_NAME': 'Test Workplan',
                    'WP_STATUS': 'Signed',
                    'WPA_GEOLOCATIONS': {'GEOLOCATION': {'P_CODE': 'LO', "AREA_NAME": "Location"}},
                    "WPA_ID": "191865",
                    "WPA_TITLE": "KI-ER 2024: SOCIAL AND BEHAVIOR CHANGE AND COMMUNICATION",
                    "WPA_DESCRIPTION": "KI-ER 2024: Social and behavior change and communication",
                    "WP_ID": "147813",
                    "WPA_START_DATE": "01-JAN-24",
                    "WPA_END_DATE": "31-DEC-24",
                    "TOTAL_BUDGET": "1234",
                    "WPA_IMPLEMENTING_PARTNERS": {
                        "IMPL_PARTNER": {
                            "IMPLEMENTING_PARTNER_CODE": cls.partner.vendor_number,
                            "IMPLEMENTING_PARTNER_NAME": cls.partner.name,
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

    def test_convert_records(self):
        synchronizer = EWPsSynchronizer(business_area_code=self.tenant.business_area_code)
        result = synchronizer._convert_records(self.sample_input)

        self.assertEqual(len(result), 7)
        self.assertIn('0060/A0/07', result['remote_cps'])
        self.assertEqual(result['remote_partners'], {self.partner.vendor_number})
        self.assertEqual(result['remote_locations'], {'LO'})
        for key, map_key in zip(
                ['description', 'title', 'total_budget', 'ewp_key_intervention', 'workplan', 'wpa_id', 'wbs'],
                ['WPA_DESCRIPTION', 'WPA_TITLE', 'TOTAL_BUDGET', 'VISION_ACTIVITY_WBS', 'WP_GID', 'WPA_ID', 'WPA_GID']):
            self.assertEqual(
                result['activities']['0060/A0/07/885/006/001/WPA0001'][key],
                self.sample_input['ROWSET']['ROW'][0][map_key])

        for key, map_key in zip(
                ['category_type', 'cost_center_code', 'cost_center_name', 'country_programme', 'ewp_id', 'name', 'plan_type', 'status'],
                ['PLAN_CATEGORY_TYPE', 'COST_CENTER_CODE', 'COST_CENTER_NAME', 'CP_WBS', 'WP_ID', 'WP_NAME', 'PLAN_TYPE', 'WP_STATUS']):
            self.assertEqual(
                result['remote_ewps']['WP/0060A007/000143/01'][key],
                self.sample_input['ROWSET']['ROW'][0][map_key])

        for key, map_key in zip(['wbs', 'workplan'], ['VISION_ACTIVITY_WBS', 'WP_GID']):
            self.assertEqual(
                result['remote_kis'][0][key],
                self.sample_input['ROWSET']['ROW'][0][map_key])

        self.assertEqual(
            result['remote_outputs'][0]['workplan'],
            self.sample_input['ROWSET']['ROW'][0]['WP_GID'])

    def test_clean_records(self):
        synchronizer = EWPsSynchronizer(business_area_code=self.tenant.business_area_code)

        result = synchronizer._clean_records(self.sample_input['ROWSET']['ROW'])

        self.assertIn('0060/A0/07', result['remote_cps'])
        self.assertEqual(len(result['remote_ewps']), 1)
        self.assertEqual(len(result['activities']), 1)

    def test_clean_records_missing_partners_still_includes_activity(self):
        synchronizer = EWPsSynchronizer(business_area_code=self.tenant.business_area_code)

        sample = deepcopy(self.sample_input)
        # Remove partners entirely to simulate upstream RAM issue
        del sample['ROWSET']['ROW'][0]['WPA_IMPLEMENTING_PARTNERS']

        result = synchronizer._clean_records(sample['ROWSET']['ROW'])

        # Activity should still be present
        self.assertEqual(len(result['activities']), 1)
        # No partners collected
        self.assertEqual(result['remote_partners'], set())

    def test_activity_created_without_partners_then_updated_with_partners(self):
        # Prerequisites from TestEWPSynchronizer
        cp = CountryProgrammeFactory(wbs='0060/A0/07', name='CP')
        out = ResultFactory(
            wbs='0060/A0/07/885/006',
            name='Output',
            result_type=ResultTypeFactory(name=ResultType.OUTPUT)
        )
        ki = ResultFactory(
            wbs='0060/A0/07/885/006/001',
            name='KI',
            result_type=ResultTypeFactory(name=ResultType.ACTIVITY)
        )
        loc = LocationFactory(p_code='LO', name='Country', admin_level=0)

        partner = self.partner

        base_data = {
            'remote_cps': [cp.wbs],
            'remote_outputs': [{
                'wbs': out.wbs,
                'workplan': 'WP/0060A007/000143/01'
            }],
            'remote_kis': [{
                'wbs': ki.wbs,
                'output': out.wbs,
                'workplan': 'WP/0060A007/000143/01'
            }],
            'remote_partners': [],
            'remote_locations': [loc.p_code],
            'remote_ewps': {
                'WP/0060A007/000143/01': {
                    'ewp_id': '152539',
                    'wbs': 'WP/0060A007/000143/01',
                    'name': 'WP',
                    'status': 'Signed',
                    'cost_center_code': '0060B00000',
                    'cost_center_name': 'CC',
                    'category_type': 'Section',
                    'plan_type': 'Annual',
                    'country_programme': cp.wbs,
                },
            },
            'activities': {
                '0060/A0/07/885/006/001/WPA0001': {
                    'wbs': '0060/A0/07/885/006/001/WPA0001',
                    'wpa_id': '187033',
                    'start_date': datetime.date(2025, 1, 1),
                    'end_date': datetime.date(2025, 12, 31),
                    'title': 'A',
                    'description': 'D',
                    'total_budget': 0,
                    'locations': [loc.p_code],
                    # partners intentionally missing/empty in first run
                    'partners': [],
                    'ewp_key_intervention': ki.wbs,
                    'workplan': 'WP/0060A007/000143/01',
                }
            }
        }

        # First run: create activity with no partners
        sync1 = EWPSynchronizer(deepcopy(base_data))
        sync1.update_workplans()
        sync1.update_ewp_outputs()
        sync1.update_kis()
        total_data, total_updated, total_new = sync1.update_activities()
        self.assertEqual(total_new, 1)

        act = EWPActivity.objects.get(wbs='0060/A0/07/885/006/001/WPA0001')
        self.assertEqual(act.partners.count(), 0)

        # Second run: same activity now has partners upstream
        with_partners = deepcopy(base_data)
        with_partners['remote_partners'] = [partner.organization.vendor_number]
        with_partners['activities']['0060/A0/07/885/006/001/WPA0001']['partners'] = [partner.organization.vendor_number]

        sync2 = EWPSynchronizer(with_partners)
        # Only activities update is needed to reflect M2M changes
        total_data2, total_updated2, total_new2 = sync2.update_activities()
        self.assertEqual(total_updated2, 1)
        act.refresh_from_db()
        self.assertEqual(list(act.partners.values_list('pk', flat=True)), [partner.pk])
