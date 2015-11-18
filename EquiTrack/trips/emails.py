__author__ = 'jcranwellward'
import datetime

from django.db.models import Q

from EquiTrack.utils import BaseEmail


class TripCreatedEmail(BaseEmail):

    template_name = 'trips/trip/created/updated'
    description = ('The email that is sent to the supervisor,'
                   ' budget owner, traveller for any update')
    subject = 'eTools {{environment}} - Trip {{number}} has been {{state}} for {{owner_name}}'
    content = """
    Dear Colleague,

    Trip {{number}} has been {{state}} for {{owner_name}} here:
    {{url}}
    Purpose of travel: {{ purpose_of_travel }}

    Thank you.
    """

    def get_context(self):
        return {
            'trip_reference': self.object.reference(),
            'owner_name': self.object.owner.get_full_name(),
            'number': self.object.reference(),
            'state': 'Submitted',
            'url': 'http://{}{}'.format(
                self.get_current_site().domain,
                self.object.get_admin_url()),
            'purpose_of_travel': self.object.purpose_of_travel,
            'environment': self.get_environment()
        }


class TripUpdatedEmail(TripCreatedEmail):

    def get_context(self):
        context = super(TripUpdatedEmail, self).get_context()
        context['state'] = 'Updated'
        return context


class TripApprovedEmail(TripCreatedEmail):

    template_name = 'trips/trip/approved'
    description = 'The email that is sent to the traveller if a trip has been approved'
    subject = "eTools {{environment}} - Trip Approved: {{trip_reference}}"
    content = """
    The following trip has been approved: {{trip_reference}}

    {{url}}

    Thank you.
    """


class TripCancelledEmail(TripCreatedEmail):

    template_name = 'trips/trip/cancelled'
    description = 'The email that is sent to everyone if a trip has been cancelled'
    subject = "eTools {{environment}} - Trip Cancelled: {{trip_reference}}"
    content = """
    The following trip has been cancelled: {{trip_reference}}

    {{url}}

    Thank you.
    """


class TripCompletedEmail(TripCreatedEmail):

    template_name = 'trips/trip/completed'
    description = 'The email that is sent to travelller and supervisor  when a trip has been completed'
    subject = "eTools {{environment}} - Trip Completed: {{trip_reference}}"
    content = """
    The following trip has been completed: {{trip_reference}}

    {{url}}

    Thank you.
    """


class TripRepresentativeEmail(TripCreatedEmail):

    template_name = 'trips/trip/representative'
    description = 'The email that is sent to the rep  to approve a trip'
    subject = "eTools {{environment}} - Trip Approval Needed: {{trip_reference}}"
    content = """
    The following trip needs representative approval: {{trip_reference}}

    {{url}}

    Thank you.
    """


class TripTravelAssistantEmail(TripCreatedEmail):

    template_name = "travel/trip/travel_or_admin_assistant"
    description = ("This e-mail will be sent when the trip is approved by the supervisor. "
                   "It will go to the travel assistant to prompt them to organise the travel "
                   "(vehicles, flights etc.) and request security clearance.")
    subject = "eTools {{environment}} - Travel for {{owner_name}}"
    content = """
    Dear {{travel_assistant}},

    Please organise the travel and security clearance (if needed) for the following trip:

    {{url}}

    Thanks,
    {{owner_name}}
    """

    def get_context(self):
        context = super(TripTravelAssistantEmail, self).get_context()
        context['travel_assistant'] = self.object.travel_assistant.first_name
        return context


class TripTAEmail(TripCreatedEmail):

    template_name = 'trips/trip/TA_request'
    description = ("This email is sent to the relevant programme assistant to create "
                    "the TA for the staff in concern after the approval of the supervisor.")
    subject = "eTools {{environment}} - Travel Authorization request for {{owner_name}}"
    content = """
    Dear {{pa_assistant}},

    Kindly draft my Travel Authorization in Vision based on the approved trip:

    {{url}}

    Thanks,
    {{owner_name}}
    """

    def get_context(self):
        context = super(TripTAEmail, self).get_context()
        context['pa_assistant'] = self.object.programme_assistant.first_name
        return context


class TripTADraftedEmail(TripCreatedEmail):

    template_name = 'trips/trip/TA_drafted'
    description = ("This email is sent to the relevant colleague to approve "
                   "the TA for the staff in concern after the TA has been drafted in VISION.")
    subject = "eTools {{environment}} - Travel Authorization drafted for {{owner_name}}"
    content = """
    Dear {{vision_approver}},"

    Kindly approve my Travel Authorization ({{ta_ref}}) in VISION based on the approved trip:

    {{url}}"

    Thanks,
    {{owner_name}}
    """

    def get_context(self):
        context = super(TripTADraftedEmail, self).get_context()
        context['vision_approver'] = self.object.vision_approver.first_name
        context['ta_ref'] = self.object.ta_reference
        return context


class TripActionPointCreated(BaseEmail):

    template_name = 'trips/action/created'
    description = 'Sent when trip action points are created'
    subject = 'eTools {{environment}} - Trip action point {{state}} for trip: {{trip_reference}}'
    content = """
    Trip action point by {{owner_name}} for {{responsible}} was {{state}}:"

    {{url}}

    Thank you.
    """

    def __init__(self, action):
        super(TripActionPointCreated, self).__init__(action.trip)
        self.action = action

    def get_context(self):
        return {
            'trip_reference': self.object.reference(),
            'url': 'http://{}{}#reporting'.format(
                self.get_current_site().domain,
                self.object.get_admin_url()
            ),
            'owner_name': self.object.owner.get_full_name(),
            'responsible': self.action.person_responsible.get_full_name(),
            'state': 'Created',
            'environment': self.get_environment()
        }


class TripActionPointUpdated(TripActionPointCreated):

    def get_context(self):
        context = super(TripActionPointUpdated, self).get_context()
        context['state'] = 'Updated'
        return context


class TripActionPointClosed(TripActionPointUpdated):

    def get_context(self):
        context = super(TripActionPointClosed, self).get_context()
        context['state'] = 'Closed'
        return context


class TripSummaryEmail(BaseEmail):

    template_name = 'trips/trip/summary'
    description = 'A summary of trips sent to the owner'
    subject = "eTools {{environment}} - Trip Summary"
    content = """
    The following is a trip summary for this week:
    <br/>
    <br/>
    <b>Trips Coming up:</b>
        <ul>
            {% for key, value in trips_coming_text.items %}
                <li><a href='{{ value.0. }}'>{{key}}</a> - started on {{ value.1 }}</li>
            {% endfor %}
        </ul>

    <b>Overdue Trips:</b>
        <ul>
            {% for key, value in trips_overdue_text.items %}
                <li><a href='{{ value.0 }}'>{{key}}</a> - ended on {{ value.1 }} </li>
            {% endfor %}
        </ul>


    Thank you.
    """

    def get_context(self):
        trips_coming_text = {}
        trips_overdue_text = {}

        trips_coming = self.object.trips.filter(
            Q(status='approved') | Q(status='submitted'),
            from_date__gt=datetime.date.today()
        )

        trips_overdue = self.object.trips.filter(
            status='approved',
            to_date__lt=datetime.date.today()
        )

        for trip in trips_overdue:
            trips_overdue_text[trip.purpose_of_travel] = ['http://{}{}'.format(
                self.get_current_site().domain,
                trip.get_admin_url()), trip.from_date.strftime("%d-%b-%y")]

        for trip in trips_coming:
            trips_coming_text[trip.purpose_of_travel] = ['http://{}{}'.format(
                self.get_current_site().domain,
                trip.get_admin_url()), trip.from_date.strftime("%d-%b-%y")]

        return {
            'trips_coming_text': trips_coming_text,
            'trips_overdue_text': trips_overdue_text,
            'owner_name': self.object.get_full_name(),
            'environment': self.get_environment()
        }


