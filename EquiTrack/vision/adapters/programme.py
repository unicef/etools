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
            # Find the country programme:
            try:
                country_programme, created = CountryProgramme.objects.get_or_create(
                    wbs=result["COUNTRY_PROGRAMME_WBS"],
                )
            except CountryProgramme.MultipleObjectsReturned as exp:
                exp.message += 'Result Structure: ' + result['COUNTRY_PROGRAMME_NAME']
                raise

            if (country_programme.name != result['COUNTRY_PROGRAMME_NAME']) or \
                    country_programme.from_date != wcf_json_date_as_datetime(result['CP_START_DATE']) or \
                    country_programme.to_date != wcf_json_date_as_datetime(result['CP_END_DATE']):

                country_programme.name = result['COUNTRY_PROGRAMME_NAME']
                country_programme.from_date = wcf_json_date_as_datetime(result['CP_START_DATE'])
                country_programme.to_date = wcf_json_date_as_datetime(result['CP_END_DATE'])
                country_programme.save()


            try:
                outcome, created = Result.objects.get_or_create(
                    country_programme=country_programme,
                    result_type=ResultType.objects.get_or_create(name='Outcome')[0],
                    wbs=result['OUTCOME_WBS'],
                )
                if not created:
                    # check if any of the information on the result is changing...
                    if outcome.name != result['OUTCOME_DESCRIPTION'] or \
                            outcome.from_date != wcf_json_date_as_datetime(result['OUTCOME_START_DATE']) or \
                            outcome.to_date != wcf_json_date_as_datetime(result['OUTCOME_END_DATE']):
                        # TODO: this outcome has been updated ... make sure there are no conflicts with
                        # the signed workplan
                        pass

                outcome.name = result['OUTCOME_DESCRIPTION']
                outcome.from_date = wcf_json_date_as_datetime(result['OUTCOME_START_DATE'])
                outcome.to_date = wcf_json_date_as_datetime(result['OUTCOME_END_DATE'])
                if not outcome.valid_entry():
                    raise Exception('Wbs of outcome does not map under country_programme')
                outcome.save()

                output, created = Result.objects.get_or_create(
                    country_programme=country_programme,
                    result_type=ResultType.objects.get_or_create(name='Output')[0],
                    wbs=result['OUTPUT_WBS'],
                )
                if not created:
                    # check if any of the information on the result is changing...
                    if output.name != result['OUTPUT_DESCRIPTION'] or \
                           output.from_date != wcf_json_date_as_datetime(result['OUTPUT_START_DATE']) or \
                           output.to_date != wcf_json_date_as_datetime(result['OUTPUT_END_DATE']) or \
                           output.name != result['OUTPUT_DESCRIPTION']:
                        # TODO: this output has been updated ... make sure there are no conflicts with
                        # the signed workplan
                        pass

                output.from_date = wcf_json_date_as_datetime(result['OUTPUT_START_DATE'])
                output.to_date = wcf_json_date_as_datetime(result['OUTPUT_END_DATE'])
                output.parent = outcome
                if not output.valid_entry():
                    raise Exception('Wbs of output does not map under country_programme')
                output.save()

                activity, created = Result.objects.get_or_create(
                    country_programme=country_programme,
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
                if not activity.valid_entry():
                    raise Exception('Wbs of activity does not map under country_programme')
                activity.save()
                processed += 1
            except Result.MultipleObjectsReturned as exp:
                exp.message += 'Outcome WBS: ' + result['OUTCOME_WBS'] \
                            + ' Output WBS: ' + result['OUTPUT_WBS'] \
                            + ' Activity WBS: ' + result['ACTIVITY_WBS']
                raise

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
            if result.wbs:
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
