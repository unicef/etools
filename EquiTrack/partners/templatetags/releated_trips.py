import tablib

from django import template
from django.utils.datastructures import SortedDict

from partners.models import PCA
from trips.models import Trip

register = template.Library()


@register.simple_tag
def show_trips(value):

    if not value:
        return ''

    intervention = PCA.objects.get(id=int(value))
    trips = Trip.objects.filter(pcas__in=[intervention])
    trip_summary = SortedDict()
    data = tablib.Dataset()

    for num, trip in enumerate(trips):
        row = SortedDict()
        row['Reason'] = trip.purpose_of_travel

    if trip_summary:
        data.headers = trip_summary.keys()
        for row in trip_summary.values():
            data.append(row.values())

        return data.html

    return '<p>No trips</p>'