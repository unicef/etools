__author__ = 'jcranwellward'

from django.conf import settings

from EquiTrack.utils import BaseExportResource
from users.models import UserProfile
from .models import Trip, ActionPoint


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

        pcas = [pca.__unicode__() for pca in trip.pcas.all()]

        self.insert_column(
            row,
            'Interventions',
            ', '.join(set(pcas))
        )

    def fill_trip_partners(self, row, trip):

        partners = set([pca.partner.name for pca in trip.pcas.all()])
        partners.union(
            set([partner.name for partner in trip.partners.all()])
        )

        self.insert_column(
            row,
            'Partners',
            ', '.join(set(partners))
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
        self.fill_trip_routes(row, trip)


class ActionPointResource(BaseExportResource):

    class Meta:
        model = ActionPoint

    def fill_row(self, action, row):

        self.insert_column(row, 'Trip', action.trip.__unicode__())
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
