import logging

from django.core.management import BaseCommand
from django.db import transaction
from post_office.models import EmailTemplate

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create Notifications command'

    @transaction.atomic
    def handle(self, *args, **options):

        logger.info(u'Command started')

        # TripCreatedEmail/TripUpdatedEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/created/updated',
            defaults={
                'description': 'The email that is sent to the supervisor, budget owner, traveller for any update',
                'subject': 'eTools {{environment}} - Trip {{number}} has been {{state}} for {{owner_name}}',
                'content': """
                Dear Colleague,

                Trip {{number}} has been {{state}} for {{owner_name}} here:
                {{url}}
                Purpose of travel: {{ purpose_of_travel }}

                Thank you.
                """,
                'html_content': """
                Dear Colleague,
                <br/>
                Trip {{number}} has been {{state}} for {{owner_name}} here:
                <br/>
                {{url}}
                <br/>
                Purpose of travel: {{ purpose_of_travel }}
                <br/>
                Thank you.
                """
            }
        )

        # TripApprovedEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/approved',
            defaults={
                'description': 'The email that is sent to the traveller if a trip has been approved',
                'subject': 'eTools {{environment}} - Trip Approved: {{trip_reference}}',
                'content': """
                The following trip has been approved: {{trip_reference}}

                {{url}}

                Thank you.
                """,
                'html_content': """
                The following trip has been approved: {{trip_reference}}
                <br/>
                {{url}}
                <br/>
                Thank you.
                """
            }
        )

        # TripApprovedEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/approved',
            defaults={
                'description': 'The email that is sent to the traveller if a trip has been approved',
                'subject': 'eTools {{environment}} - Trip Approved: {{trip_reference}}',
                'content': """
                The following trip has been approved: {{trip_reference}}

                {{url}}

                Thank you.
                """,
                'html_content': """
                The following trip has been approved: {{trip_reference}}
                <br/>
                {{url}}
                <br/>
                Thank you.
                """
            }
        )

        # TripCancelledEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/cancelled',
            defaults={
                'description': 'The email that is sent to everyone if a trip has been cancelled',
                'subject': 'eTools {{environment}} - Trip Cancelled: {{trip_reference}}',
                'content': """
                The following trip has been cancelled: {{trip_reference}}

                {{url}}

                Thank you.
                """,
                'html_content': """
                The following trip has been cancelled: {{trip_reference}}
                <br/>
                {{url}}
                <br/>
                Thank you.
                """
            }
        )

        # TripCompletedEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/completed',
            defaults={
                'description': 'The email that is sent to travelller and supervisor  when a trip has been completed',
                'subject': 'eTools {{environment}} - Trip Completed: {{trip_reference}}',
                'content': """
                The following trip has been completed: {{trip_reference}}

                {{url}}

                Action Points:

                {{action_points}}

                Thank you.
                """,
                'html_content': """
                The following trip has been completed: {{trip_reference}}
                <br/>
                {{url}}
                <br/>
                Action Points:
                <br/>
                {{action_points}}
                <br/>
                Thank you.
                """
            }
        )

        # TripRepresentativeEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/representative',
            defaults={
                'description': 'The email that is sent to the rep  to approve a trip',
                'subject': 'eTools {{environment}} - Trip Approval Needed: {{trip_reference}}',
                'content': """
                The following trip needs representative approval: {{trip_reference}}

                {{url}}

                Thank you.
                """,
                'html_content': """
                The following trip needs representative approval: {{trip_reference}}
                <br/>
                {{url}}
                <br/>
                Thank you.
                """
            }
        )

        # TripTravelAssistantEmail
        EmailTemplate.objects.update_or_create(
            name='travel/trip/travel_or_admin_assistant',
            defaults={
                'description': 'This e-mail will be sent when the trip is approved by the supervisor. It will go to the'
                               'travel assistant to prompt them to organise the travel (vehicles, flights etc.) and'
                               'request security clearance.',
                'subject': 'eTools {{environment}} - Travel for {{owner_name}}',
                'content': """
                Dear {{travel_assistant}},

                Please organise the travel and security clearance (if needed) for the following trip:

                {{url}}

                Thanks,
                {{owner_name}}
                """,
                'html_content': """
                Dear {{travel_assistant}},
                <br/>
                Please organise the travel and security clearance (if needed) for the following trip:
                <br/>
                {{url}}
                <br/>
                Thanks,
                <br/>
                {{owner_name}}
                """
            }
        )

        # TripTAEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/TA_request',
            defaults={
                'description': 'This email is sent to the relevant programme assistant to create the TA for the staff'
                               ' in concern after the approval of the supervisor.',
                'subject': 'eTools {{environment}} - Travel Authorization request for {{owner_name}}',
                'content': """
                Dear {{pa_assistant}},

                Kindly draft my Travel Authorization in Vision based on the approved trip:

                {{url}}

                Thanks,
                {{owner_name}}
                """,
                'html_content': """
                Dear {{pa_assistant}},
                <br/>
                Kindly draft my Travel Authorization in Vision based on the approved trip:
                <br/>
                {{url}}
                <br/>
                Thanks,
                <br/>
                {{owner_name}}
                """
            }
        )

        # TripTADraftedEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/TA_drafted',
            defaults={
                'description': 'This email is sent to the relevant colleague to approve the TA for the staff in concern'
                               ' after the TA has been drafted in VISION.',
                'subject': 'eTools {{environment}} - Travel Authorization drafted for {{owner_name}}',
                'content': """
                Dear {{vision_approver}},"

                Kindly approve my Travel Authorization ({{ta_ref}}) in VISION based on the approved trip:

                {{url}}"

                Thanks,
                {{owner_name}}
                """,
                'html_content': """
                Dear {{vision_approver}},"
                <br/>
                Kindly approve my Travel Authorization ({{ta_ref}}) in VISION based on the approved trip:
                <br/>
                {{url}}"
                <br/>
                Thanks,
                <br/>
                {{owner_name}}
                """
            }
        )

        # TripActionPointCreated/TripActionPointUpdated/TTripActionPointClosed
        EmailTemplate.objects.update_or_create(
            name='trips/action/created/updated/closed',
            defaults={
                'description': 'Sent when trip action points are created, updated, or closed',
                'subject': 'eTools {{environment}} - Trip action point {{state}} for trip: {{trip_reference}}',
                'content': """
                Trip action point by {{owner_name}} for {{responsible}} was {{state}}:"
                {{url}}

                Thank you.
                """,
                'html_content': """
                Trip action point by {{owner_name}} for {{responsible}} was {{state}}:"
                <br/>
                {{url}}
                <br/>
                Thank you.
                """
            }
        )

        # TripSummaryEmail
        EmailTemplate.objects.update_or_create(
            name='trips/trip/summary',
            defaults={
                'description': 'A summary of trips sent to the owner',
                'subject': 'eTools {{environment}} - Trip Summary',
                'html_content': """
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
            }
        )

        # PartnershipCreatedEmail
        EmailTemplate.objects.update_or_create(
            name='partners/partnership/created/updated',
            defaults={
                'description': 'The email that is sent when a PD/SSFA is added or is updated',
                'subject': 'PD/SSFA {{number}} has been {{state}}',
                'content': """
                Dear Colleague,

                PD/SSFA {{number}} has been {{state}} here:

                {{url}}

                Thank you.
                """,
                'html_content': """
                Dear Colleague,
                <br/>
                PD/SSFA {{number}} has been {{state}} here:
                <br/>
                {{url}}
                <br/>
                Thank you.
                """
            }
        )

        # TPM
        EmailTemplate.objects.update_or_create(
            name='partners/partnership/signed/frs',
            defaults={
                'description': 'Partnership signed with future start date that has no Fund Reservations',
                'subject': 'eTools Intervention {{ number }} does not have any FRs',
                'content': """
                Dear Colleague,

                Please note that the Partnership ref. {{ number }} with {{ partner }} is signed, the start date for the
                PD/SSFA is {{ start_date }} and there is no FR associated with this partnership in eTools.
                Please log into eTools and add the FR number to the record, so that the programme document/SSFA status
                 can change to active.

                {{ url }}.

                Please note that this is an automated message and any response to this email cannot be replied to.
                """
            }
        )
        EmailTemplate.objects.update_or_create(
            name='partners/partnership/ended/frs/outstanding',
            defaults={
                'description': 'PD Status ended And FR Amount does not equal the Actual Amount.',
                'subject': 'eTools Partnership {{ number }} Fund Reservations',
                'content': """
                Dear Colleague,

                Please note that the Partnership ref. {{ number }} with {{ partner }} has ended but the disbursement
                amount is less than the FR amount.
                Please follow-up with the IP or adjust your FR.

                {{ url }}.

                Please note that this is an automated message and any response to this email cannot be replied to.
                """,
            }
        )

        EmailTemplate.objects.update_or_create(
            name='partners/partnership/ending',
            defaults={
                'description': 'PD Ending in 30 or 15 days.',
                'subject': 'eTools Partnership {{ number }} is ending in {{ days }} days',
                'content': """
                Dear Colleague,

                Please note that the Partnership ref {{ number }} with {{ partner }} will end in {{ days }} days.
                Please follow-up with the Implementing Partner on status of implementation, which may require an
                amendment.

                {{ url }}.

                Please note that this is an automated message and any response to this email cannot be replied to.
                """
            }
        )

        # Auditor Portal
        EmailTemplate.objects.get_or_create(name='audit/engagement/submit_to_auditor')
        EmailTemplate.objects.get_or_create(name='audit/engagement/reported_by_auditor')
        EmailTemplate.objects.get_or_create(name='audit/staff_member/appointed_to_engagement')
        EmailTemplate.objects.get_or_create(name='audit/engagement/action_point_assigned')
        EmailTemplate.objects.get_or_create(name='audit/staff_member/invite')

        # TPM Notifications
        EmailTemplate.objects.get_or_create(name='tpm/visit/assign')
        EmailTemplate.objects.get_or_create(name='tpm/visit/reject')
        EmailTemplate.objects.get_or_create(name='tpm/visit/accept')
        EmailTemplate.objects.get_or_create(name='tpm/visit/generate_report')
        EmailTemplate.objects.get_or_create(name='tpm/visit/report')
        EmailTemplate.objects.get_or_create(name='tpm/visit/report_rejected')
        EmailTemplate.objects.get_or_create(name='tpm/visit/approve_report')
        EmailTemplate.objects.get_or_create(name='tpm/visit/approve_report_tpm')
        EmailTemplate.objects.get_or_create(name='tpm/visit/action_point_assigned')
        EmailTemplate.objects.get_or_create(name='organisations/staff_member/invite')
        EmailTemplate.objects.get_or_create(name='organisations/staff_member/set_password')

        logger.info(u'Command finished')
