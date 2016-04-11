import json
import datetime

from reports.models import ResultStructure, ResultType, Result, Indicator
from vision.utils import wcf_json_date_as_datetime
from vision.vision_data_synchronizer import VisionDataSynchronizer


class ProgrammeSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetProgrammeStructureList_JSON'
    REQUIRED_KEYS = (
        "COUNTRY_PROGRAMME_NAME",
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
        last_year = datetime.datetime(today.year-1, 1, 1)

        def in_time_range(record):
            end = wcf_json_date_as_datetime(record['OUTCOME_END_DATE'])
            if end >= last_year:
                return True
            return False

        return filter(in_time_range, records)

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        for result in filtered_records:
            result_structure, created = ResultStructure.objects.get_or_create(
                name=result['COUNTRY_PROGRAMME_NAME'],
                from_date=wcf_json_date_as_datetime(result['CP_START_DATE']),
                to_date=wcf_json_date_as_datetime(result['CP_END_DATE']),
            )

            outcome, created = Result.objects.get_or_create(
                result_structure=result_structure,
                result_type=ResultType.objects.get_or_create(name='Outcome')[0],
                wbs=result['OUTCOME_WBS'],
            )
            outcome.name = result['OUTCOME_DESCRIPTION']
            outcome.from_date = wcf_json_date_as_datetime(result['OUTCOME_START_DATE'])
            outcome.to_date = wcf_json_date_as_datetime(result['OUTCOME_END_DATE'])
            outcome.save()

            output, created = Result.objects.get_or_create(
                result_structure=result_structure,
                result_type=ResultType.objects.get_or_create(name='Output')[0],
                wbs=result['OUTPUT_WBS'],
            )
            output.name = result['OUTPUT_DESCRIPTION']
            output.from_date = wcf_json_date_as_datetime(result['OUTPUT_START_DATE'])
            output.to_date = wcf_json_date_as_datetime(result['OUTPUT_END_DATE'])
            output.parent = outcome
            output.save()

            activity, created = Result.objects.get_or_create(
                result_structure=result_structure,
                result_type=ResultType.objects.get_or_create(name='Activity')[0],
                wbs=result['ACTIVITY_WBS'],
            )
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
            activity.save()
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

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):

        results = Result.objects.filter(result_type__name='Output')
        lookup = {}
        for result in results:
            lookup[result.wbs.replace('/', '')+'000'] = result

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
                indicator.name = ram_indicator['INDICATOR_DESCRIPTION']
                indicator.baseline = ram_indicator['BASELINE']
                indicator.target = ram_indicator['TARGET']
                indicator.save()

                result.ram = True
                result.save()
                processed += 1

        return processed
