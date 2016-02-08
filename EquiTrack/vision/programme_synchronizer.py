import json
import datetime

from django.conf import settings

from reports.models import ResultStructure, ResultType, Result
from vision.utils import wcf_json_date_as_datetime
from .vision_data_synchronizer import VisionDataSynchronizer


class ProgrammeSynchronizer(VisionDataSynchronizer):

    PROGRAMME_URL = settings.VISION_URL + 'GetProgrammeStructureList_JSON/'
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

    def __init__(self, country):

        super(ProgrammeSynchronizer, self).__init__(
            country,
            ProgrammeSynchronizer.PROGRAMME_URL + country.business_area_code
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
