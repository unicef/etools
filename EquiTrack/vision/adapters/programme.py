import json
import datetime

import logging
from django.db import transaction

from reports.models import ResultType, Result, Indicator, CountryProgramme
from vision.utils import wcf_json_date_as_date
from vision.vision_data_synchronizer import VisionDataSynchronizer

logger = logging.getLogger(__name__)


class ResultStructureSynchronizer(object):
    def __init__(self, data):
        self.data = data
        self.cps = {}
        self.outcomes = {}
        self.outputs = {}
        self.activities = {}

    def _update_changes(self, local, remote):
        updated = False
        for k in remote:
            if getattr(local, k) != remote[k]:
                updated = True
                setattr(local, k, remote[k])

        return updated

    def _get_local_parent(self, wbs, parent_type):
        parent_map = {
            # 10 is the number of characters for a cp wbs
            'cp': (10, self.cps),
            'outcome': (14, self.outcomes),
            'output': (18, self.outputs)
        }
        parent_group = parent_map[parent_type][1]
        wbs_length = parent_map[parent_type][0]
        return parent_group.get(wbs[:wbs_length], None)

    def update_cps(self):
        remote_cps = self.data['cps']
        total_data = len(remote_cps)
        total_updated = 0

        local_cps = dict([(r.wbs, r) for r in CountryProgramme.objects.filter(wbs__in=list(remote_cps.keys()))])

        for local_cp in local_cps.values():
            if self._update_changes(local_cp, remote_cps[local_cp.wbs]):
                print('Updated {}'.format(local_cp))
                total_updated += 1
                local_cp.save()
            del remote_cps[local_cp.wbs]

        # Normally a bulk save, but in this case there are very few records, and things are calculated on save:
        new_cps = {}
        for remote_cp in remote_cps.values():
            new_cps[remote_cp['wbs']], _ = CountryProgramme.objects.get_or_create(**remote_cp)

        # add the newly created cps
        local_cps.update(new_cps)
        self.cps = local_cps

        return total_data, total_updated, len(new_cps)

    def update_outcomes(self):
        remote_outcomes = self.data['outcomes']
        OUTCOME_TYPE = ResultType.objects.get(name=ResultType.OUTCOME)
        total_data = len(remote_outcomes)
        total_updated = 0

        local_outcomes = dict([(r.wbs, r) for r in Result.objects.filter(wbs__in=list(remote_outcomes.keys()),
                                                                         result_type__name=ResultType.OUTCOME
                                                                         )])

        for local_outcome in local_outcomes.values():
            if self._update_changes(local_outcome, remote_outcomes[local_outcome.wbs]):
                print('Updated {}'.format(local_outcome))
                local_outcome.save()
                total_updated += 1
            del remote_outcomes[local_outcome.wbs]

        new_outcomes = {}
        for remote_outcome in remote_outcomes.values():
            remote_outcome['country_programme'] = self._get_local_parent(remote_outcome['wbs'], 'cp')
            remote_outcome['result_type'] = OUTCOME_TYPE

            new_outcomes[remote_outcome['wbs']], _ = Result.objects.get_or_create(**remote_outcome)

        # add the newly created cps
        local_outcomes.update(new_outcomes)
        self.outcomes = local_outcomes
        return total_data, total_updated, len(new_outcomes)

    def update_outputs(self):
        rem_outputs = self.data['outputs']
        OUTPUT_TYPE = ResultType.objects.get(name=ResultType.OUTPUT)
        total_data = len(rem_outputs)
        total_updated = 0

        loc_outputs = dict([(r.wbs, r) for r in Result.objects.filter(wbs__in=list(rem_outputs.keys()),
                                                                      result_type__name=ResultType.OUTPUT)])

        for loc_output in loc_outputs.values():
            if self._update_changes(loc_output, rem_outputs[loc_output.wbs]):
                print('Updated {}'.format(loc_output))
                loc_output.save()
                total_updated += 1
            del rem_outputs[loc_output.wbs]

        new_outputs = {}
        for rem_output in rem_outputs.values():
            rem_output['country_programme'] = self._get_local_parent(rem_output['wbs'], 'cp')
            rem_output['parent'] = self._get_local_parent(rem_output['wbs'], 'outcome')
            rem_output['result_type'] = OUTPUT_TYPE

            new_outputs[rem_output['wbs']], _ = Result.objects.get_or_create(**rem_output)

        # add the newly created cps
        loc_outputs.update(new_outputs)
        self.outputs = loc_outputs
        return total_data, total_updated, len(new_outputs)

    def update_activities(self):
        rem_activities = self.data['activities']
        ACTIVITY_TYPE = ResultType.objects.get(name=ResultType.ACTIVITY)
        total_data = len(rem_activities)
        total_updated = 0

        loc_activities = dict([(r.wbs, r) for r in Result.objects.filter(wbs__in=list(rem_activities.keys()),
                                                                         result_type__name=ResultType.ACTIVITY)])

        for loc_activity in loc_activities.values():
            if self._update_changes(loc_activity, rem_activities[loc_activity.wbs]):
                print('Updated {}'.format(loc_activity))
                loc_activity.save()
                total_updated += 1
            del rem_activities[loc_activity.wbs]

        new_activities = {}
        for rem_activity in rem_activities.values():
            rem_activity['country_programme'] = self._get_local_parent(rem_activity['wbs'], 'cp')
            rem_activity['parent'] = self._get_local_parent(rem_activity['wbs'], 'output')
            rem_activity['result_type'] = ACTIVITY_TYPE

            new_activities[rem_activity['wbs']], _ = Result.objects.get_or_create(**rem_activity)

        # add the newly created cps
        loc_activities.update(new_activities)
        self.outputs = loc_activities
        return total_data, total_updated, len(new_activities)

    @transaction.atomic
    def update(self):
        # update / add new cps
        total_cps = self.update_cps()
        cps = 'CPs updated: Total {}, Updated {}, New {}'.format(*total_cps)

        # update / add new Outcomes
        total_outcomes = self.update_outcomes()
        outcomes = 'Outcomes updated: Total {}, Updated {}, New {}'.format(*total_outcomes)

        # update / add new Outputs
        total_outputs = self.update_outputs()
        outputs = 'Outputs updated: Total {}, Updated {}, New {}'.format(*total_outputs)

        # update / add new Activities
        total_activities = self.update_activities()
        activities = 'Activities updated: Total {}, Updated {}, New {}'.format(*total_activities)

        return {
            'details': '\n'.join([cps, outcomes, outputs, activities]),
            'total_records': sum([i[0] for i in [total_cps, total_outcomes, total_outputs, total_activities]]),
            'processed': sum([i[1] + i[2] for i in [total_cps, total_outcomes, total_outputs, total_activities]])
        }


class ProgrammeSynchronizer(VisionDataSynchronizer):
    ENDPOINT = 'GetProgrammeStructureList_JSON'
    REQUIRED_KEYS = (
        "COUNTRY_PROGRAMME_NAME",
        "COUNTRY_PROGRAMME_WBS",
        "CP_START_DATE",
        "CP_END_DATE",
        "OUTCOME_AREA_CODE",
        "OUTCOME_AREA_NAME",
        "OUTCOME_AREA_NAME_LONG",
        "OUTCOME_WBS",
        "OUTCOME_DESCRIPTION",
        "OUTCOME_START_DATE",
        "OUTCOME_END_DATE",
        "OUTPUT_WBS",
        "OUTPUT_DESCRIPTION",
        "OUTPUT_START_DATE",
        "OUTPUT_END_DATE",
        "ACTIVITY_WBS",
        "ACTIVITY_DESCRIPTION",
        "ACTIVITY_START_DATE",
        "ACTIVITY_END_DATE",
        "SIC_CODE",
        "SIC_NAME",
        "GIC_CODE",
        "GIC_NAME",
        "ACTIVITY_FOCUS_CODE",
        "ACTIVITY_FOCUS_NAME",
        "GENDER_MARKER_CODE",
        "GENDER_MARKER_NAME",
        "HUMANITARIAN_TAG",
        "HUMANITARIAN_MARKER_CODE",
        "HUMANITARIAN_MARKER_NAME",
        "PROGRAMME_AREA_CODE",
        "PROGRAMME_AREA_NAME",
    )
    DATES = (
        "CP_START_DATE",
        "CP_END_DATE",
        "OUTCOME_START_DATE",
        "OUTCOME_END_DATE",
        "OUTPUT_START_DATE",
        "OUTPUT_END_DATE",
        "ACTIVITY_START_DATE",
        "ACTIVITY_END_DATE"
    )
    CP_MAP = (
        ("COUNTRY_PROGRAMME_NAME", "name"),
        ("COUNTRY_PROGRAMME_WBS", "wbs"),
        ("CP_START_DATE", "from_date"),
        ("CP_END_DATE", "to_date")
    )
    OUTCOME_MAP = (
        ("OUTCOME_AREA_CODE", "code"),
        ("OUTCOME_WBS", "wbs"),
        ("OUTCOME_DESCRIPTION", "name"),
        ("OUTCOME_START_DATE", "from_date"),
        ("OUTCOME_END_DATE", "to_date"),
    )
    OUTPUT_MAP = (
        ("OUTPUT_WBS", "wbs"),
        ("OUTPUT_DESCRIPTION", "name"),
        ("OUTPUT_START_DATE", "from_date"),
        ("OUTPUT_END_DATE", "to_date"),
    )
    ACTIVITY_MAP = (
        ("ACTIVITY_WBS", "wbs"),
        ("ACTIVITY_DESCRIPTION", "name"),
        ("ACTIVITY_START_DATE", "from_date"),
        ("ACTIVITY_END_DATE", "to_date"),
        ("SIC_CODE", "sic_code"),
        ("SIC_NAME", "sic_name"),
        ("GIC_CODE", "gic_code"),
        ("GIC_NAME", "gic_name"),
        ("ACTIVITY_FOCUS_CODE", "activity_focus_code"),
        ("ACTIVITY_FOCUS_NAME", "activity_focus_name"),
        ("HUMANITARIAN_TAG", "humanitarian_tag"),
        # ("PROGRAMME_AREA_CODE", "code"),
        # ("PROGRAMME_AREA_NAME", ""),
    )

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def _filter_by_time_range(self, records):
        records = super(ProgrammeSynchronizer, self)._filter_records(records)

        today = datetime.datetime.today()
        last_year = datetime.datetime(today.year - 1, 1, 1).date()

        def in_time_range(record):
            if record['OUTCOME_END_DATE'] >= last_year:
                return True
            return False

        return filter(in_time_range, records)

    def _clean_records(self, records):
        records = self._filter_by_time_range(records)
        cps = {}
        outcomes = {}
        outputs = {}
        activities = {}

        for r in records:
            if not cps.get(r['COUNTRY_PROGRAMME_WBS'], None):
                cps[r['COUNTRY_PROGRAMME_WBS']] = dict([(i[1], r[i[0]]) for i in self.CP_MAP])

            if not outcomes.get(r['OUTCOME_WBS'], None):
                outcomes[r['OUTCOME_WBS']] = dict([(i[1], r[i[0]]) for i in self.OUTCOME_MAP])

            if not outputs.get(r['OUTPUT_WBS'], None):
                outputs[r['OUTPUT_WBS']] = dict([(i[1], r[i[0]]) for i in self.OUTPUT_MAP])

            if not activities.get(r['ACTIVITY_WBS'], None):
                activities[r['ACTIVITY_WBS']] = dict([(i[1], r[i[0]]) for i in self.ACTIVITY_MAP])

        return {'cps': cps, 'outcomes': outcomes, 'outputs': outputs, 'activities': activities}

    def _convert_records(self, records):
        records = json.loads(records.get('GetProgrammeStructureList_JSONResult', []))
        for r in records:
            for k in self.DATES:
                r[k] = wcf_json_date_as_date(r[k])
            r['HUMANITARIAN_TAG'] = r['HUMANITARIAN_TAG'] not in ['No', 'None', '0']

        return self._clean_records(records)

    def _save_records(self, records):
        # print records[0]
        # TODO maybe ? save to file in azure somewhere at this point.. have a separate task to read from file and update

        synchronizer = ResultStructureSynchronizer(records)

        return synchronizer.update()


class RAMSynchronizer(VisionDataSynchronizer):
    ENDPOINT = 'GetRAMInfo_JSON'
    REQUIRED_KEYS = (
        "INDICATOR_DESCRIPTION",
        "INDICATOR_CODE",
        "WBS_ELEMENT_CODE",
        "BASELINE",
        "TARGET",
    )

    def _convert_records(self, records):
        return json.loads(records)

    def _changed_fields(self, fields, local_obj, api_obj):
        for field in fields:
            obj_value = api_obj[self.MAPPING[field]][:255]
            if field in ['name']:
                obj_value = api_obj[self.MAPPING[field]][:1024]
            if getattr(local_obj, field) != obj_value:
                return True
        return False

    def _save_records(self, records):

        processed = self.process_indicators(records)

        return processed

    def _clean_records(self, records):
        records = self._filter_records(records)
        wbss = []
        mapped_records = {}
        for r in records:
            a = r['WBS_ELEMENT_CODE']
            code = unicode(r['INDICATOR_CODE'])
            mapped_records[code] = {
                'name': r['INDICATOR_DESCRIPTION'][:1024],
                'baseline': r['BASELINE'][:255],
                'code': code,
                'target': r['TARGET'][:255],
                'ram_indicator': True,
                'result__wbs': '/'.join([a[0:4], a[4:6], a[6:8], a[8:11], a[11:14]])
            }
            wbss.append(mapped_records[code]['result__wbs'])
        return mapped_records, wbss

    def process_indicators(self, records):
        updated = 0
        skipped_update = 0
        skipped_creation = 0

        fields_that_can_change = ['name', 'baseline', 'target', 'result__wbs']
        # get all the indicators that are present in our db:
        records, wbss = self._clean_records(records)

        results = Result.objects.filter(result_type__name='Output', wbs__in=wbss).all()
        result_map = dict([(r.wbs, r) for r in results])

        existing_records = Indicator.objects.filter(code__in=records.keys()).prefetch_related('result').all()

        for er in existing_records:
            # remote record:
            rr = records[er.code]
            record_needs_saving = False
            for field in fields_that_can_change:
                if field == 'result__wbs':
                    if not er.result:
                        try:
                            missing_result = Result.objects.get(wbs=rr[field])
                        except Result.DoesNotExist:
                            logger.error('Indicator missing result {}'.format(er.id))
                            break
                        else:
                            er.result = missing_result
                            record_needs_saving = True
                            continue
                    if er.result.wbs != rr[field]:
                        try:
                            er.result = result_map[rr[field]]
                        except KeyError:
                            skipped_update += 1
                            logger.error('Result not found for wbs {} for indicator with code {}'.format(rr[field],
                                                                                                         er.code))
                        else:
                            record_needs_saving = True
                elif getattr(er, field) != rr[field]:
                        setattr(er, field, rr[field])
                        record_needs_saving = True
            if record_needs_saving:
                updated += 1
                er.save()

        list_of_existing_codes = [er.code for er in existing_records]

        records_to_create = []
        for r in records.items():
            if r[0] in list_of_existing_codes:
                continue
            try:
                r[1]['result'] = result_map[r[1].pop('result__wbs', None)]
            except KeyError:
                skipped_creation += 1
                logger.error('Result not found for non-existent indicator with code {}'.format(r[1]['code']))
            else:
                records_to_create.append(r[1])

        created = Indicator.objects.bulk_create([Indicator(**r) for r in records_to_create])

        # print('Total Remote', len(wbss))
        # print('Created, ', len(created))
        # print('Updated, ', updated)
        # print('Created Skipped, ', skipped_creation)
        # print('Updated Skipped, ', skipped_update)

        indicators_activated = Indicator.objects.filter(code__in=records.keys()).filter(active=False).update(
            active=True)

        indicators_deactivated = Indicator.objects.exclude(code__in=records.keys()).exclude(active=False).update(
            active=False)

        return {
            'details': '\n'.join([
                'Created Skipped {}'.format(skipped_creation),
                'Updated Skipped {}'.format(skipped_update),
                'Created {}'.format(len(created)),
                'Indicators Updated to Active {}'.format(indicators_activated),
                'Indicators Updated to Inactive {}'.format(indicators_deactivated),
                'Updated {}'.format(updated)
            ]),
            'total_records': len(wbss),
            'processed': len(created) + updated
        }
