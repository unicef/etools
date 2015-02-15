__author__ = 'jcranwellward'


from EquiTrack.utils import BaseExportResource
from .models import Trip, ActionPoint


class TripResource(BaseExportResource):

    class Meta:
        model = Trip

    def fill_trip_routes(self, row, trip):

        self.insert_column(
            row,
            'Destinations',
            ', '.join([route.destination for route in trip.travelroutes_set.all()])
        )

        return row

    def fill_trip_partners(self, row, trip):

        partners = [pca.partner.name for pca in trip.pcas.all()]
        partners.extend(
            [partner.name for partner in trip.partners.all()]
        )

        self.insert_column(
            row,
            'Partners',
            ', '.join(set(partners))
        )

    def fill_trip_row(self, row, trip):

        self.insert_column(row, 'Status', trip.status)
        self.insert_column(row, 'Traveller', trip.owner.get_full_name())
        self.insert_column(row, 'Supervisor', trip.supervisor.get_full_name())
        self.insert_column(row, 'Section', trip.section.name if trip.section else '')
        self.insert_column(row, 'Office', trip.office.name if trip.office else '')
        self.insert_column(row, 'Purpose', trip.purpose_of_travel)
        self.insert_column(row, 'From Date', str(trip.from_date))
        self.insert_column(row, 'To Date', str(trip.to_date))

        return row

    def fill_row(self, trip, row):

        self.fill_trip_row(row, trip)
        self.fill_trip_partners(row, trip)
        self.fill_trip_routes(row, trip)


class ActionPointResource(BaseExportResource):

    class Meta:
        model = ActionPoint

    def fill_row(self, action, row):

        self.insert_column(row, 'Trip', action.trip.__unicode__())
        self.insert_column(row, 'Traveller', action.trip.owner)
        self.insert_column(row, 'Description', action.description)
        self.insert_column(row, 'Due Date', action.due_date)
        self.insert_column(
            row,
            'Persons Responsible',
            ', '.join([person.get_full_name()
                       for person in action.persons_responsible.all()])
        )
        self.insert_column(row, 'Actions Taken', action.actions_taken)
        self.insert_column(
            row,
            'Completed Date',
            action.completed_date.strftime("%d-%m-%Y")
            if action.completed_date else ''
        )
        self.insert_column(row, 'Supervisors Comments', action.comments)
        self.insert_column(row, 'Supervisors Comments', action.comments)
        self.insert_column(row, 'Closed?', action.closed)
