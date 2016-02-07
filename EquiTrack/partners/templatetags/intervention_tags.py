__author__ = 'unicef-leb-inn'

import tablib

from django import template
from django.utils.datastructures import SortedDict

from partners.models import PCA
from trips.models import Trip


register = template.Library()


@register.simple_tag
def show_work_plan(value):

    if not value:
        return ''

    intervention = PCA.objects.get(id=int(value))
    results = intervention.results.all()
    data = tablib.Dataset()
    work_plan = SortedDict()

    for num, result in enumerate(results):
        row = SortedDict()
        row['Code'] = result.indicator.code if result.indicator else result.result.code
        row['Details'] = result.indicator.name if result.indicator else result.result.name
        row['Targets'] = result.target if result.target else ''
        if result.disaggregation:
            row.update(result.disaggregation)
        row['Total'] = result.total if result.total else ''
        row['CSO'] = result.partner_contribution if result.partner_contribution else ''
        row['UNICEF Cash'] = result.unicef_cash if result.unicef_cash else ''
        row['UNICEF Supplies'] = result.in_kind_amount if result.in_kind_amount else ''

        work_plan[num] = row

    if work_plan:
        for row in work_plan.values():
            if not data.headers or len(data.headers) < len(row.values()):
                data.headers = row.keys()
            data.append(row.values())

        return data.html

    return '<p>No results</p>'


@register.simple_tag
def show_trips(value):

    if not value:
        return ''

    intervention = PCA.objects.get(id=int(value))
    trips = Trip.objects.filter(pcas__in=[intervention])
    data = tablib.Dataset()
    trip_summary = []

    for trip in trips:
        row = SortedDict()
        row['Ref'] = '<a href="{}">{}</a>'.format(trip.get_admin_url(), trip.reference())
        row['Status'] = trip.status
        row['Traveller'] = trip.owner
        row['Trip Type'] = trip.travel_type
        row['Purpose'] = trip.purpose_of_travel
        row['From'] = trip.from_date
        row['To'] = trip.to_date

        trip_summary.append(row)

    if trip_summary:
        data.headers = trip_summary[0].keys()
        for row in trip_summary:
            data.append(row.values())

        return data.html

    return '<p>No trips</p>'
