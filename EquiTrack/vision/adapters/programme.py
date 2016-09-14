import json
import datetime

from reports.models import ResultStructure, ResultType, Result, Indicator, CountryProgramme
from vision.utils import wcf_json_date_as_datetime
from vision.vision_data_synchronizer import VisionDataSynchronizer


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

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def _convert_records(self, records):
        return json.loads(records.get('GetProgrammeStructureList_JSONResult', []))

    def _filter_records(self, records):
        records = super(ProgrammeSynchronizer, self)._filter_records(records)
        today = datetime.datetime.today()
        last_year = datetime.datetime(today.year - 1, 1, 1)

        def in_time_range(record):
            end = wcf_json_date_as_datetime(record['OUTCOME_END_DATE'])
            if end >= last_year:
                return True
            return False

        return filter(in_time_range, records)

    def _changed_fields(self, obj_type, fields, local_obj, api_obj):
        tmap = {
            'cp': {
                'name': "COUNTRY_PROGRAMME_NAME",
                'wbs': "COUNTRY_PROGRAMME_WBS",
                'from_date': 'CP_START_DATE',
                'to_date': 'CP_END_DATE'
            },
            'outcome': {
                'name': "OUTCOME_DESCRIPTION",
                'wbs': "OUTCOME_WBS",
                'from_date': 'OUTCOME_START_DATE',
                'to_date': 'OUTCOME_END_DATE'
            },
            'output': {
                'name': "OUTPUT_DESCRIPTION",
                'wbs': "OUTPUT_WBS",
                'from_date': 'OUTPUT_START_DATE',
                'to_date': 'OUTPUT_END_DATE'
            },
            'activity': {
                'name': "ACTIVITY_DESCRIPTION",
                'wbs': "ACTIVITY_WBS",
                'from_date': 'ACTIVITY_START_DATE',
                'to_date': 'ACTIVITY_END_DATE',
                'sic_code': 'SIC_CODE',
                'sic_name': 'SIC_NAME',
                'gic_code': 'GIC_CODE',
                'gic_name': 'GIC_NAME',
                'activity_focus_code': 'ACTIVITY_FOCUS_CODE',
                'activity_focus_name': 'ACTIVITY_FOCUS_NAME',
            }
        }
        mapping = tmap[obj_type]
        for field in fields:
            apiobj_field = api_obj[mapping[field]]
            if field.endswith('date'):
                if not wcf_json_date_as_datetime(api_obj[mapping[field]]):
                    apiobj_field = None
                else:
                    apiobj_field = wcf_json_date_as_datetime(api_obj[mapping[field]]).date()
            if getattr(local_obj, field) != apiobj_field:
                print "field changed", field, obj_type, getattr(local_obj, field), 'Changed To', apiobj_field
                return True
        return False

    def _update_record(self):
        pass

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        cps = {}
        outcomes = {}
        outputs = {}
        activities = {}

        for result in filtered_records:
            # Find the country programme:
            updating_cp = False
            country_programme = cps.get(result["COUNTRY_PROGRAMME_WBS"], None)
            if not country_programme:
                try:
                    country_programme = CountryProgramme.objects.get(
                        wbs=result["COUNTRY_PROGRAMME_WBS"],
                    )
                except CountryProgramme.DoesNotExist:
                    country_programme = CountryProgramme(
                        wbs=result["COUNTRY_PROGRAMME_WBS"]
                    )
                    updating_cp = True
                except CountryProgramme.MultipleObjectsReturned as exp:
                    exp.message += 'Result Structure: ' + result['COUNTRY_PROGRAMME_NAME']
                    raise
                else:
                    cps[result["COUNTRY_PROGRAMME_WBS"]] = country_programme

            possible_changes = ['name', 'from_date', 'to_date']
            if updating_cp or self._changed_fields('cp', possible_changes, country_programme, result):
                country_programme.name = result['COUNTRY_PROGRAMME_NAME']
                country_programme.from_date = wcf_json_date_as_datetime(result['CP_START_DATE'])
                country_programme.to_date = wcf_json_date_as_datetime(result['CP_END_DATE'])
                print country_programme
                print result
                country_programme.save()

            updating_outcome = False
            outcome = outcomes.get(result['OUTCOME_WBS'], None)
            if not outcome:
                try:
                    outcome, updating_outcome = Result.objects.get_or_create(
                        country_programme=country_programme,
                        result_type=ResultType.objects.get_or_create(name='Outcome')[0],
                        wbs=result['OUTCOME_WBS'],
                    )
                except Result.MultipleObjectsReturned as exp:
                    exp.message += 'Outcome WBS: ' + result['OUTCOME_WBS'] \
                                   + ' Output WBS: ' + result['OUTPUT_WBS'] \
                                   + ' Activity WBS: ' + result['ACTIVITY_WBS']
                    raise
                else:
                    outcomes[result['OUTCOME_WBS']] = outcome

            possible_changes = ['name', 'from_date', 'to_date']
            if updating_outcome or self._changed_fields('outcome', possible_changes, outcome, result):
                # check if any of the information on the result is changing...
                outcome.name = result['OUTCOME_DESCRIPTION']
                outcome.from_date = wcf_json_date_as_datetime(result['OUTCOME_START_DATE'])
                outcome.to_date = wcf_json_date_as_datetime(result['OUTCOME_END_DATE'])
                if not outcome.valid_entry():
                    print 'Skipping outcome because of wbs missmatch: ', outcome
                    # we need to skip this record since the wbs's don;t match
                    # TODO in these cases... send an email with the record and make the country aware
                    continue
                    # raise Exception('Wbs of outcome does not map under country_programme')
                outcome.save()

            updating_output = False
            output = outputs.get(result['OUTPUT_WBS'], None)
            if not output:
                try:
                    output, updating_output = Result.objects.get_or_create(
                        country_programme=country_programme,
                        result_type=ResultType.objects.get_or_create(name='Output')[0],
                        wbs=result['OUTPUT_WBS'],
                    )
                except Result.MultipleObjectsReturned as exp:
                    exp.message += 'Outcome WBS: ' + result['OUTCOME_WBS'] \
                                   + ' Output WBS: ' + result['OUTPUT_WBS'] \
                                   + ' Activity WBS: ' + result['ACTIVITY_WBS']
                    raise
                else:
                    outputs[result['OUTPUT_WBS']] = output

            possible_changes = ['name', 'from_date', 'to_date']
            if updating_output or self._changed_fields('output', possible_changes, output, result):
                output.name = result['OUTPUT_DESCRIPTION']
                output.from_date = wcf_json_date_as_datetime(result['OUTPUT_START_DATE'])
                output.to_date = wcf_json_date_as_datetime(result['OUTPUT_END_DATE'])
                output.parent = outcome
                if not output.valid_entry():
                    # we need to skip this record since the wbs's don;t match
                    # TODO in these cases... send an email with the record and make the country aware
                    continue
                    #raise Exception('Wbs of output does not map under country_programme')
                output.save()

            try:
                activity, updating_activity = Result.objects.get_or_create(
                    country_programme=country_programme,
                    result_type=ResultType.objects.get_or_create(name='Activity')[0],
                    wbs=result['ACTIVITY_WBS'],
                )
            except Result.MultipleObjectsReturned as exp:
                exp.message += 'Outcome WBS: ' + result['OUTCOME_WBS'] \
                               + ' Output WBS: ' + result['OUTPUT_WBS'] \
                               + ' Activity WBS: ' + result['ACTIVITY_WBS']
                raise

            possible_changes = ['name', 'from_date', 'to_date', 'sic_code', 'sic_name', 'gic_code',
                                'gic_name', 'activity_focus_code', 'activity_focus_name']

            if updating_activity or self._changed_fields('activity', possible_changes, activity, result):
                activity.name = result['ACTIVITY_DESCRIPTION']
                activity.from_date = wcf_json_date_as_datetime(result['ACTIVITY_START_DATE'])
                activity.to_date = wcf_json_date_as_datetime(result['ACTIVITY_END_DATE'])
                activity.parent = output
                activity.sic_code = result['SIC_CODE']
                activity.sic_name = result['SIC_NAME']
                activity.gic_code = result['GIC_CODE']
                activity.gic_name = result['GIC_NAME']
                activity.activity_focus_code = result['ACTIVITY_FOCUS_CODE']
                activity.activity_focus_name = result['ACTIVITY_FOCUS_NAME']
                if not activity.valid_entry():
                    activity.delete()
                    raise Exception('Wbs of activity does not map under country_programme')
                activity.save()

            if updating_cp:
                print 'add cp', country_programme
            if updating_activity:
                print 'added activity', activity
            if updating_outcome:
                print 'add outcome', outcome
            if updating_output:
                print 'add output', output
            processed += 1
        return processed


class RAMSynchronizer(VisionDataSynchronizer):
    ENDPOINT = 'GetRAMInfo_JSON'
    REQUIRED_KEYS = (
        "INDICATOR_DESCRIPTION",
        "INDICATOR_CODE",
        "WBS_ELEMENT_CODE",
        "BASELINE",
        "TARGET",
    )
    MAPPING = {
        'name': 'INDICATOR_DESCRIPTION',
        'baseline': 'BASELINE',
        'target': 'TARGET',
        'code': 'INDICATOR_CODE',
    }

    def _convert_records(self, records):
        return json.loads(records)

    def _changed_fields(self, fields, local_obj, api_obj):
        for field in fields:
            if getattr(local_obj, field) != api_obj[self.MAPPING[field]]:
                return True
        return False

    def _save_records(self, records):

        results = Result.objects.filter(result_type__name='Output')
        lookup = {}
        for result in results:
            if result.wbs:
                lookup[result.wbs.replace('/', '') + '000'] = result

        processed = 0
        filtered_records = self._filter_records(records)
        for ram_indicator in filtered_records:
            try:
                result = lookup[ram_indicator['WBS_ELEMENT_CODE']]
            except KeyError:
                print 'No result found for WBS: {}'.format(ram_indicator['WBS_ELEMENT_CODE'])
            else:
                indicator, created = Indicator.objects.get_or_create(
                    code=ram_indicator['INDICATOR_CODE'],
                    result=result,
                    ram_indicator=True,
                )
                if created or self._changed_fields(['name', 'baseline', 'target'], indicator, ram_indicator):
                    indicator.name = ram_indicator['INDICATOR_DESCRIPTION'][:1024]
                    indicator.baseline = ram_indicator['BASELINE'][:255]
                    indicator.target = ram_indicator['TARGET'][:255]
                    indicator.save()

                if not result.ram:
                    result.ram = True
                    result.save()
                processed += 1

        return processed
