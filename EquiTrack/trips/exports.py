__author__ = 'jcranwellward'

import tablib

from django.utils.datastructures import SortedDict

from import_export import resources

from .models import Trip


class TripResource(resources.ModelResource):

    headers = []

    def insert_column(self, row, field_name, value):

        row[field_name] = value if self.headers else ''

    def insert_columns_inplace(self, row, fields, after_column):

        keys = row.keys()
        before_column = None
        if after_column in row:
            index = keys.index(after_column)
            offset = index + 1
            if offset < len(row):
                before_column = keys[offset]

        for key, value in fields.items():
            if before_column:
                row.insert(offset, key, value)
                offset += 1
            else:
                row[key] = value

    def fill_trip_routes(self, row, trip):

        for num, route in enumerate(trip.travelroutes_set.all()):
            num += 1

            self.insert_column(row, 'Origin {}'.format(num), route.origin)
            self.insert_column(row, 'Depart {}'.format(num), str(route.depart))
            self.insert_column(row, 'Destination {}'.format(num), route.destination)
            self.insert_column(row, 'Arrive {}'.format(num), str(route.arrive))

        return row

    def fill_trip_row(self, row, trip):

        self.insert_column(row, 'Ref', trip.reference())
        self.insert_column(row, 'Status', trip.status)
        self.insert_column(row, 'Traveller', trip.owner.get_full_name())
        self.insert_column(row, 'Supervisor', trip.supervisor.get_full_name())
        self.insert_column(row, 'Section', trip.section.name if trip.section else '')
        self.insert_column(row, 'Office', trip.office.name if trip.office else '')
        self.insert_column(row, 'Purpose', trip.purpose_of_travel)
        self.insert_column(row, 'From Date', str(trip.from_date))
        self.insert_column(row, 'To Date', str(trip.to_date))
        self.insert_column(row, 'Travel Type', str(trip.travel_type))
        self.insert_column(row, 'TA Required', trip.ta_required)
        self.insert_column(row, 'International Travel', trip.international_travel)

        return row

    def fill_row(self, trip, row):

        self.fill_trip_row(row, trip)
        self.fill_trip_routes(row, trip)

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        rows = []

        if queryset is None:
            queryset = self.get_queryset()

        fields = SortedDict()

        for trip in queryset.iterator():

            self.fill_row(trip, fields)

        self.headers = fields

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for trip in queryset.iterator():
            # second pass creates rows from the known table shape
            row = fields.copy()

            self.fill_row(trip, row)

            rows.append(row)

        data = tablib.Dataset(headers=fields.keys())
        for row in rows:
            data.append(row.values())
        return data

    class Meta:
        model = Trip

