from collections import OrderedDict as SortedDict

from django.conf import settings
from import_export.resources import ModelResource
import tablib

from users.models import UserProfile
from trips.models import Trip, ActionPoint


class BaseExportResource(ModelResource):

    headers = []

    def insert_column(self, row, field_name, value):
        """
        Inserts a column into a row with a given value
        or sets a default value of empty string if none
        """
        row[field_name] = value

    def insert_columns_inplace(self, row, fields, after_column):
        """
        Inserts fields with values into a row inplace
        and after a specific named column
        """
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

    def fill_row(self, resource, fields):
        """
        This performs the actual work of translating
        a model into a fields dictionary for exporting.
        Inheriting classes must implement this.
        """
        return NotImplementedError()

    def export(self, queryset=None):
        """
        Exports a resource.
        """

        # TODO quickly patched.. this whole code needs to be rewritten to for performance (streaming)

        if queryset is None:
            queryset = self.get_queryset()

        if getattr(self, 'up_queryset', None):
            queryset = self.up_queryset(queryset)

        fields = SortedDict()
        data = tablib.Dataset(headers=fields.keys())

        for model in queryset.iterator():
            # first pass creates table shape
            self.fill_row(model, fields)
            data.append(fields.keys())
            # run only once for the headers
            break

        self.headers = fields

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.

        for model in queryset.all():
            # second pass creates rows from the known table shape
            row = fields.copy()
            self.fill_row(model, row)
            data.append(row.values())

        return data


class TripResource(BaseExportResource):

    class Meta:
        model = Trip

    def up_queryset(self, q):
        return q.prefetch_related('travelroutes_set',
                                  'pcas',
                                  'partners',
                                  'owner',
                                  'supervisor',
                                  'budget_owner',
                                  'section',
                                  'office',
                                  )

    def fill_trip_routes(self, row, trip):

        self.insert_column(
            row,
            'Destinations',
            ', '.join([route.destination for route in trip.travelroutes_set.all()])
        )

        return row

    def fill_trip_pcas(self, row, trip):
        pcas = set(unicode(lp.intervention) for lp in trip.linkedpartner_set.all() if lp.intervention)

        pcas.union(
            set(unicode(lgp.intervention) for lgp in trip.linkedgovernmentpartner_set.all() if lgp.intervention)
        )
        self.insert_column(
            row,
            'Interventions',
            ', '.join(set(pcas))
        )

    def fill_trip_partners(self, row, trip):

        partners = set([lp.partner.name for lp in trip.linkedpartner_set.all()])
        partners.union(
            set([lgp.partner.name for lgp in trip.linkedgovernmentpartner_set.all()])
        )

        self.insert_column(
            row,
            'Partners',
            ', '.join(set(partners))
        )

    def fill_trip_locations(self, row, trip):

        self.insert_column(
            row,
            'Locations',
            ', '.join([' - '.join((tl.location.name, tl.location.p_code))
                       for tl in trip.triplocation_set.all()
                       if tl.location and tl.location.name and tl.location.p_code])
        )

    def fill_trip_row(self, row, trip):

        self.insert_column(row, 'Status', trip.status)
        self.insert_column(row, 'Travel Type', trip.travel_type)
        self.insert_column(row, 'Traveller', trip.owner.get_full_name())
        self.insert_column(row, 'Supervisor', trip.supervisor.get_full_name())
        self.insert_column(row, 'Section', trip.section.name if trip.section else '')
        self.insert_column(row, 'Office', trip.office.name if trip.office else '')
        self.insert_column(row, 'Purpose', trip.purpose_of_travel)
        self.insert_column(row, 'International', trip.international_travel)
        self.insert_column(row, 'Budget Owner', trip.budget_owner.get_full_name() if trip.budget_owner else '')
        self.insert_column(row, 'From Date', str(trip.from_date))
        self.insert_column(row, 'To Date', str(trip.to_date))
        self.insert_column(row, 'Report', 'Yes' if trip.main_observations else 'No')
        # self.insert_column(row, 'Attachments', trip.attachments())
        self.insert_column(row, 'URL', 'https://{}{}'.format(settings.HOST, trip.get_admin_url()))
        return row

    def fill_row(self, trip, row):

        self.fill_trip_row(row, trip)
        self.fill_trip_partners(row, trip)
        self.fill_trip_pcas(row, trip)
        self.fill_trip_locations(row, trip)
        self.fill_trip_routes(row, trip)


class ActionPointResource(BaseExportResource):

    class Meta:
        model = ActionPoint

    def fill_row(self, action, row):

        self.insert_column(row, 'Trip', unicode(action.trip))
        self.insert_column(row, 'Traveller', action.trip.owner)
        self.insert_column(row, 'Section', action.trip.section)
        self.insert_column(row, 'Office', action.trip.office)
        self.insert_column(row, 'Description', action.description)
        self.insert_column(row, 'Due Date', action.due_date)
        self.insert_column(row, 'Person Responsible', action.person_responsible)
        if UserProfile.objects.filter(user_id=action.person_responsible.id).exists():
            self.insert_column(row, 'Responsible Section', action.person_responsible.profile.section)
            self.insert_column(row, 'Responsible Office', action.person_responsible.profile.office)

        self.insert_column(row, 'Actions Taken', action.actions_taken)
        self.insert_column(
            row,
            'Completed Date',
            action.completed_date.strftime("%d-%m-%Y")
            if action.completed_date else ''
        )
        self.insert_column(row, 'Supervisors Comments', action.comments)
        self.insert_column(row, 'Status', action.status)
        self.insert_column(row, 'Created', action.created_date)
