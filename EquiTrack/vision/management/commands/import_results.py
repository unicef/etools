__author__ = 'jcranwellward'


import json
import datetime

from django.core.management.base import BaseCommand

from reports.models import ResultStructure, ResultType, Result


class Command(BaseCommand):
    help = 'Imports programme structures from VISION'

    def handle(self, *args, **options):

        path = args[0]
        with open(path) as file:
            data = json.load(file)

            for result in data:

                result_structure, created = ResultStructure.objects.get_or_create(
                    name=result['COUNTRY_PROGRAMME_NAME'],
                    from_date=datetime.date(2011, 1, 1),
                    to_date=datetime.date(2015, 12, 31),
                )

                outcome, created = Result.objects.get_or_create(
                    result_structure=result_structure,
                    result_type=ResultType.objects.get_or_create(name='Outcome')[0],
                    wbs=result['OUTCOME_WBS'],
                )
                outcome.name = result['OUTCOME_DESCRIPTION']
                outcome.save()

                output, created = Result.objects.get_or_create(
                    result_structure=result_structure,
                    result_type=ResultType.objects.get_or_create(name='Output')[0],
                    wbs=result['OUTPUT_WBS'],
                )
                output.name = result['OUTPUT_DESCRIPTION']
                output.parent = outcome
                output.save()

                activity, created = Result.objects.get_or_create(
                    result_structure=result_structure,
                    result_type=ResultType.objects.get_or_create(name='Activity')[0],
                    wbs=result['ACTIVITY_WBS'],
                )
                activity.name = result['ACTIVITY_DESCRIPTION']
                activity.parent = output

                activity.sic_code = result['SIC_CODE']
                activity.sic_name = result['SIC_NAME']
                activity.gic_code = result['GIC_CODE']
                activity.gic_name = result['GIC_NAME']
                activity.activity_focus_code = result['ACTIVITY_FOCUS_CODE']
                activity.activity_focus_name = result['ACTIVITY_FOCUS_NAME']
                activity.save()
