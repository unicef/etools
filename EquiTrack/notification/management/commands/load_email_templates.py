from django.core.management.base import NoneCommand

from post_office.models import EmailTemplate


class Command(NoneCommand):
    help = "Create post_office EmailTemplate objects."

    def handle(self, *args, **options):
        # TripCreatedEmail/TripUpdatedEmail
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/created/updated',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/approved',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/approved',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/cancelled',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/completed',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/representative',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'travel/trip/travel_or_admin_assistant',
            defaults={
                'description': 'This e-mail will be sent when the trip is approved by the supervisor. It will go to the travel assistant to prompt them to organise the travel (vehicles, flights etc.) and request security clearance.',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/TA_request',
            defaults={
                'description': 'This email is sent to the relevant programme assistant to create the TA for the staff in concern after the approval of the supervisor.',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/TA_drafted',
            defaults={
                'description': 'This email is sent to the relevant colleague to approve the TA for the staff in concern after the TA has been drafted in VISION.',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/action/created/updated/closed',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'trips/trip/summary',
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
        template, created = EmailTemplate.objects.update_or_create(
            template_name = 'partners/partnership/created/updated',
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
