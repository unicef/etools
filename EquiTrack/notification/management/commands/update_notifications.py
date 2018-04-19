import logging

from django.core.management import BaseCommand
from django.db import transaction
from post_office.models import EmailTemplate

from utils.common.utils import strip_text

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

        # Base
        EmailTemplate.objects.update_or_create(
            name='base',
            defaults={
                'description': 'Base template for emails.',
                'html_content': """
                {% load static %}
                <!DOCTYPE html>
                <html>
                  <head>
                    <meta name="viewport" content="width=device-width">
                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
                    <title>{% block title %}{% endblock %}</title>
                    <style type="text/css">
                      /* -------------------------------------
                          RESPONSIVE AND MOBILE FRIENDLY STYLES
                      ------------------------------------- */
                      @media only screen and (max-width: 620px) {
                        table[class=body] p,
                        table[class=body] ul,
                        table[class=body] ol,
                        table[class=body] td,
                        table[class=body] span,
                        table[class=body] a {}
                        table[class=body] .wrapper,
                        table[class=body] .article {
                          padding: 16px !important; }
                        table[class=body] .content {
                          padding: 10px !important; }
                        table[class=body] .container {
                          padding: 0 !important;
                          width: 100% !important; }
                        table[class=body] .main {
                          border-left-width: 0 !important;
                          border-radius: 0 !important;
                          border-right-width: 0 !important; }
                        table[class=body] .header,
                        table[class=body] .footer {
                          padding-left: 16px !important;
                          padding-right: 16px !important; }
                        table[class=body] .footer td {
                          vertical-align: bottom !important; }
                        table[class=body] .footer .links .br {
                          display: inline !important; }
                        table[class=body] .img-responsive {
                          height: auto !important;
                          max-width: 100% !important;
                          width: auto !important; }
                      }
                      @media only screen and (max-width: 480px) {
                        table[class=data-table] {
                          margin: 0 !important;
                          background-color: #F2F2F2;
                        }
                        table[class=data-table] .dt,
                        table[class=data-table] .df {
                          display: block !important;
                          width: 100% !important; }
                        table[class=data-table] .dt {
                          font-size: 12px !important;
                          padding: 8px 8px 4px !important;
                          background-color: transparent !important;
                          border-bottom: 0 !important; }
                        table[class=data-table] .df {
                          font-size: 14px !important;
                          padding: 0 8px 6px !important; }
                      }
                      @media only screen and (max-width: 320px) {
                        table[class=body] h1 {
                          font-size: 18px !important; }
                        table[class=body] .btn table {
                          width: 100% !important; }
                        table[class=body] .btn a {
                          width: 100% !important; }
                        table[class=data-table] .dt {
                          font-size: 11px !important; }
                        table[class=data-table] .df {
                          font-size: 13px !important; }
                      }
                      /* -------------------------------------
                          PRESERVE THESE STYLES IN THE HEAD
                      ------------------------------------- */
                      @media all {
                        .ExternalClass {
                          width: 100%; }
                        .ExternalClass,
                        .ExternalClass p,
                        .ExternalClass span,
                        .ExternalClass font,
                        .ExternalClass td,
                        .ExternalClass div {
                          line-height: 100%; }
                        .apple-link a {
                          color: inherit !important;
                          font-family: inherit !important;
                          font-size: inherit !important;
                          font-weight: inherit !important;
                          line-height: inherit !important;
                          text-decoration: none !important; }
                        .btn-primary table td:hover {
                          background-color: #0099FF !important; }
                        .btn-primary a:hover {
                          background-color: #0099FF !important;
                          border-color: #0099FF !important; }
                      }
                    </style>
                  </head>
                  <body style="background-color:#EEEEEE;font-family:sans-serif;-webkit-font-smoothing:antialiased;
                               font-size:14px;line-height:1.4;margin:0;padding:0;-ms-text-size-adjust:100%;
                               -webkit-text-size-adjust:100%;">
                    <table border="0" cellpadding="0" cellspacing="0" class="body"
                           style="border-collapse:separate;mso-table-lspace:0pt;mso-table-rspace:0pt;
                           background-color:#EEEEEE;width:100%;">
                      <tr>
                        <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">&nbsp;</td>
                        <td class="container" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                                     display:block;max-width:580px;padding:10px;width:580px;
                                                     margin:0 auto !important;width:auto !important;">
                          <!-- START CENTERED WHITE CONTAINER -->
                          <div class="content" style="box-sizing:border-box;display:block;margin:0 auto;
                                                      max-width:580px;padding:10px 0;">
                            <!-- START MAIN CONTENT AREA -->
                            <table border="0" cellpadding="0" cellspacing="0" class="main"
                                   style="border-collapse:separate;mso-table-lspace:0pt;mso-table-rspace:0pt;
                                   background:#FFFFFF;border-radius:3px;width:100%;
                                   box-shadow:0 0 2px rgba(0,0,0,.12), 0 2px 2px rgba(0,0,0,.24);">
                              <!-- START HEADER -->
                              <tr>
                                <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                                          box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                                          padding:16px 20px 12px;overflow:hidden;
                                                          background-color:#233944;border-radius:3px 3px 0 0;">
                                  <table border="0" cellpadding="0" cellspacing="0"
                                         style="border-collapse:separate;mso-table-lspace:0pt;
                                         mso-table-rspace:0pt;width:100%;">
                                    <tr>
                                      <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">
                                        <!-- TODO: update image link with global -->
                                        <a href="http://etools.unicef.org" target="_blank"
                                           style="color:#0099FF;text-decoration:none;">
                                          <span style="color: white;text-decoration: none;">eTools</span>
                                        </a>
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>
                              <!-- END HEADER -->
                              <!-- START CONTENT -->
                              <tr>
                                <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                                           box-sizing:border-box;padding:20px;">
                                  <table border="0" cellpadding="0" cellspacing="0"
                                         style="border-collapse:separate;mso-table-lspace:0pt;
                                         mso-table-rspace:0pt;width:100%;">
                                    <tr>
                                      <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">
                                          {% block content %}
                                          {% endblock %}
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>
                              <!-- END CONTENT -->
                              <tr>
                                <td class="footer"
                                    style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                    box-sizing:border-box;width:100%;max-height:56px;padding:14px 20px 14px;
                                    overflow:hidden;background-color:#E5F4FF;border-radius:0 0 3px 3px;">
                                  <table border="0" cellpadding="0" cellspacing="0"
                                         style="border-collapse:separate;mso-table-lspace:0pt;
                                         mso-table-rspace:0pt;width:100%;">
                                    <tr>
                                      <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">
                                        <!-- TODO: update image link with global -->
                                        <a href="http://unicef.org" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;">

                                           <img src='http://etools.unicef.org/static/img/UNICEF_logo_Cyan.png'
                                                alt="Unicef" class="logo-unicef" width="101" height="24"
                                                style="border:none;-ms-interpolation-mode:bicubic;max-width:100%;
                                                       display:block;margin:0;padding:0;width:101px;height:24px;"/>
                                       </a>
                                      </td>
                                      <td class="links" style="font-family:sans-serif;font-size:14px;
                                                               vertical-align:top;text-align:right;">
                                        <!-- TODO: add links -->
                                        <!--
                                        <a href="#" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;display:inline-block;
                                           margin:0;padding:4px;margin-left:10px;font-size:12px;text-decoration:none;">
                                            Contact
                                        </a>
                                        <span class="br" style="display:none;"><br/></span>

                                        <a href="#" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;display:inline-block;
                                           margin:0;padding:4px;margin-left:10px;font-size:12px;text-decoration:none;">
                                            Disclaimer
                                        </a>
                                        <span class="br" style="display:none;"><br/></span>

                                        <a href="#" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;display:inline-block;
                                           margin:0;padding:4px;margin-left:10px;font-size:12px;text-decoration:none;">
                                            Privacy Policy
                                        </a>
                                        <span class="br" style="display:none;"><br/></span>
                                        -->
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>
                              <!-- START FOOTER -->
                              <!-- END FOOTER -->
                            </table>
                            <!-- END MAIN CONTENT AREA -->
                          </div>
                          <!-- END CENTERED WHITE CONTAINER -->
                        </td>
                        <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">&nbsp;</td>
                      </tr>
                    </table>
                  </body>
                </html>
                """
            }
        )

        # ID management
        EmailTemplate.objects.update_or_create(
            name='email_auth/token/login',
            defaults={
                'description': 'The email that is sent to user to login without password.',
                'subject': 'eTools Access Token',
                'content': strip_text("""
                    Dear {{ recipient }},

                    Please click on this link to sign in to eTools portal:

                    {{ login_link }}

                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block title %}eTools Access Token{% endblock %}

                    {% block content %}
                    <p>Dear {{ recipient }},</p>

                    <p>Please click on <a href="{{ login_link }}">this link</a> to sign in to eTools portal.</p>

                    <p>Thank you.</p>
                    {% endblock %}
                """
            }
        )

        # Firms notifications
        EmailTemplate.objects.update_or_create(
            name='organisations/staff_member/invite',
            defaults={
                'description': 'The email that is sent to partner staff member when he have been '
                               'registered in the system.',
                'subject': 'eTools {% if environment %}{{ environment }} {% endif %}- Invitation',

                'content': strip_text("""
                    Dear Colleague,

                    You have been invited to the eTools. To get access to our system follow link.

                    {{ login_link }}

                    eTools Team
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block title %}eTools {% if environment %}{{ environment }} {% endif %}- Invitation{% endblock %}

                    {% block content %}
                    <p>Dear Colleague,</p>

                    <p>
                        You have been invited to the <b>eTools</b>.
                        To get access to our system follow <a href="{{ login_link }}">link</a>.
                    </p>

                    <p style="text-align:right">eTools Team</p>
                    {% endblock %}
                """
            }
        )

        # Auditor Portal
        EmailTemplate.objects.update_or_create(
            name='audit/engagement/submit_to_auditor',
            defaults={
                'description': 'Email that send to auditor when engagement have been created.',
                'subject': '[Auditor Portal] ACCESS GRANTED for {{ engagement.engagement_type }}, '
                           '{{ engagement.unique_id }}',

                'content': strip_text("""
                    Dear {{ staff_member }},

                    UNICEF is granting you access to the Financial Assurance Module in eTools.
                    Please refer below for additional information.

                    Engagement Type: {{ engagement.engagement_type }}
                    Partner: {{ engagement.partner }}

                    Please click this link to complete the report: {{ engagement.object_url }}

                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ staff_member }},<br/><br/>

                    UNICEF is granting you access to the Financial Assurance Module in eTools.<br/>
                    Please refer below for additional information.<br/><br/>

                    Engagement Type: {{ engagement.engagement_type }}<br/>
                    Partner: {{ engagement.partner }}<br/><br/>

                    Please click <a href="{{ engagement.object_url }}">this link</a> to complete the report.<br/><br/>

                    Thank you.
                    {% endblock %}
                """
            }
        )
        EmailTemplate.objects.update_or_create(
            name='audit/engagement/reported_by_auditor',
            defaults={
                'description': 'Email that send when auditor fill engagement\'s report.',
                'subject': '{{ engagement.auditor_firm }} has completed the final report for '
                           '{{ engagement.engagement_type }}, {{ engagement.unique_id }}',

                'content': strip_text("""
                    Dear {{ focal_point }},

                    {{ engagement.auditor_firm }} has completed the final report for {{ engagement.engagement_type }}.
                    Please refer below for additional information.

                    Engagement Type: {{ engagement.engagement_type }}
                    Partner: {{ engagement.partner }}

                    Please click this link to view the final report: {{ engagement.object_url }}

                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ focal_point }},<br/><br/>

                    {{ engagement.auditor_firm }} has completed the final report for {{ engagement.engagement_type }}.
                    Please refer below for additional information.<br/><br/>

                    Engagement Type: {{ engagement.engagement_type }}<br/>
                    Partner: {{ engagement.partner }}<br/><br/>

                    Please click <a href="{{ engagement.object_url }}">this link</a> to view the final report.<br/><br/>

                    Thank you.
                    {% endblock %}
                """
            }
        )
        EmailTemplate.objects.update_or_create(
            name='audit/engagement/action_point_assigned',
            defaults={
                'description': 'Engagement action point was assigned',
                'subject': '[eTools] ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',

                'content': strip_text("""
                    Dear {{ action_point.person_responsible }},

                    {{ action_point.author }} has assigned you an action point.

                    Engagement ID: {{ engagement.unique_id }}
                    Category: {{ action_point.category }}
                    Due Date: {{ action_point.due_date}}
                    Link: {{ engagement.object_url }}

                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ action_point.person_responsible }},<br/><br/>

                    {{ action_point.author }} has assigned you an action point. <br/><br/>

                    Engagement ID: {{ engagement.unique_id }}<br/>
                    Category: {{ action_point.category }}<br/>
                    Due Date: {{ action_point.due_date}}<br/>
                    Link: <a href="{{ engagement.object_url }}">click here</a><br/><br/>

                    Thank you.
                    {% endblock %}
                """
            }
        )
        EmailTemplate.objects.update_or_create(
            name='audit/staff_member/invite',
            defaults={
                'description': 'Invite staff member to auditor portal',
                'subject': 'UNICEF Auditor Portal Access',

                'content': strip_text("""
                    Dear {{ staff_member }},

                    UNICEF has assingned a {{ engagement.engagement_type }} to you.
                    Please click link to gain access to the UNICEF Auditor Portal.

                    {{ login_link }}

                    eTools Team
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block title %}UNICEF Auditor Portal Access{% endblock %}

                    {% block content %}

                    <p>Dear {{ staff_member }},</p>

                    <p>UNICEF has assingned a {{ engagement.engagement_type }} to you.
                    Please click <a href="{{ login_link }}">link</a> to gain access to the UNICEF Auditor Portal.</p>

                    <p style="text-align:right">eTools Team</p>
                    {% endblock %}
                """
            }
        )

        # TPM Notifications
        EmailTemplate.objects.update_or_create(
            name='tpm/visit/assign',
            defaults={
                'description': 'Visit assigned. TPM should be notified.',
                'subject': '[TPM Portal] TPM Visit Request for {{ visit.partners }}; {{ visit.reference_number }}',

                'content': strip_text("""
                    Dear {{ visit.tpm_partner }},

                    UNICEF is requesting a Monitoring/Verification Visit for {{ visit.partners }}.
                    Please refer below for additional information.
                    {% for activity in visit.tpm_activities %}
                    PD/SSFA/ToR: {{ activity.intervention }}
                    CP Output {{ activity.cp_output }}, {{ activity.locations }}

                    {% endfor %}
                    Please click this link for additional information and documents related to the visit:
                    {{ visit.object_url }}

                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ visit.tpm_partner }},<br/>
                    <br/>
                    UNICEF is requesting a Monitoring/Verification Visit for <b>{{ visit.partners }}</b>. <br/><br/>
                    Please refer below for additional information.<br/><br/>
                    {% for activity in visit.tpm_activities %}
                    <b>PD/SSFA/ToR</b>: {{ activity.intervention }}<br/>
                    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
                    <b>Locations</b>: {{ activity.locations }}</br>
                    <b>Section</b>: {{ activity.section }}<br/><br/>
                    {% endfor %}
                    <br/>
                    Please click this link for additional information and documents related to the visit:
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/>
                    <br/>
                    Thank you.
                    {% endblock %}
                """
            }
        )

        EmailTemplate.objects.update_or_create(
            name='tpm/visit/reject',
            defaults={
                'description': 'TPM rejected visit. Notify focal points.',
                "subject": "{{ visit.tpm_partner }} has rejected the Monitoring/Verification Visit Request "
                           "{{ visit.reference_number }}",
                "content": strip_text("""
                    Dear {{ recipient }},

                    TPM {{ visit.tpm_partner }} has rejected your request for a Monitoring/Verifcation visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}

                    Please click this link for additional information and reason for rejection {{ visit.object_url }}

                    Thank you.
                """),
                "html_content": """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ recipient }},<br/>
                    <br/>
                    TPM <b>{{ visit.tpm_partner }}</b> has rejected your request for a Monitoring/Verifcation visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
                    <br/><br/>
                    Please click this link for additional information and reason for rejection
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/>
                    <br/>
                    Thank you.
                    {% endblock %}
                """,
            }
        )

        EmailTemplate.objects.update_or_create(
            name='tpm/visit/accept',
            defaults={
                "description": "TPM accepted visit. Notify focal points & PME.",
                "subject": "{{ visit.tpm_partner }} has accepted the Monitoring/Verification Visit Request "
                           "{{ visit.reference_number }}",

                "content": strip_text("""
                    Dear {{ recipient }},

                    TPM {{ visit.tpm_partner }} has accepted your request for a Monitoring/Verifcation visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}

                    Please click this link for additional information {{ visit.object_url }}

                    Thank you.
                """),

                "html_content": """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ recipient }},<br/><br/>

                    TPM <b>{{ visit.tpm_partner }}</b> has accepted your request for a Monitoring/Verifcation visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
                    <br/><br/>

                    Please click this link for additional information
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/><br/>

                    Thank you.
                    {% endblock %}
                """,
            }
        )

        EmailTemplate.objects.update_or_create(
            name='tpm/visit/report',
            defaults={
                'description': 'TPM finished with visit report.  Notify PME & focal points.',
                'subject': '{{ visit.tpm_partner }} has submited the final report for {{ visit.reference_number }}',

                'content': strip_text("""
                    Dear {{ recipient }},

                    {{ visit.tpm_partner }} has submited the final report for the Monitoring/Verification
                    visit{% if partnerships %} requested for {{ visit.interventions }}{% endif %}.
                    Please refer below for additional information.

                    {% for activity in visit.tpm_activities %}
                    PD/SSFA/ToR: {{ activity.intervention}}
                    CP Output: {{ activity.cp_output }}
                    Location: {{ activity.locations }}
                    Section: {{ activity.section }}
                    {% endfor %}

                    Please click this link to view the final report: {{ visit.object_url }} and take
                    the appropriate action {Accept/Request for more information}
                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ recipient }},<br/>
                    <br/>
                    <b>{{ visit.tpm_partner }}</b> has submited the final report for the Monitoring/Verification
                    visit{% if partnerships %} requested for <b>{{ visit.interventions }}</b>{% endif %}.<br/>
                    Please refer below for additional information.<br/>
                    <br/>
                    {% for activity in visit.tpm_activities %}
                    <b>PD/SSFA/ToR</b>: {{ activity.intervention }}<br/>
                    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
                    <b>Locations</b>: {{ activity.locations }}</br>
                    <b>Section</b>: {{ activity.section }}<br/><br/>
                    {% endfor %}
                    <br/>
                    Please click this link to view the final report:
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a> and take
                    the appropriate action {Accept/Request for more information}<br/><br/>
                    Thank you.
                    {% endblock %}
                """
            }
        )

        EmailTemplate.objects.update_or_create(
            name='tpm/visit/report_rejected',
            defaults={
                'description': 'Report was rejected. Notify TPM.',
                'subject': 'Request for more information on the Final report for the Monitoring/Verification Visit '
                           '{{ visit.reference_number }}',

                'content': strip_text("""
                    UNICEF has requested additional information on  the final report submited for
                    the Monitoring/Verification visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}.
                    Please refer below for additional information.

                    {% for activity in visit.tpm_activities %}
                    PD/SSFA/ToR: {{ activity.intervention}}
                    CP Output: {{ activity.cp_output }}
                    Location: {{ activity.locations }}
                    Section: {{ activity.section }}

                    {% endfor %}

                    Please click this link to view the additional information/clarifications requested:
                    {{ visit.object_url }}
                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ recipient }},<br/>
                    <br/>
                    UNICEF has requested additional information on  the final report submited for
                    the Monitoring/Verification visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
                    <br/>
                    Please refer below for additional information.<br/>
                    <br/>
                    {% for activity in visit.tpm_activities %}
                    <b>PD/SSFA/ToR</b>: {{ activity.intervention }}<br/>
                    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
                    <b>Locations</b>: {{ activity.locations }}</br>
                    <b>Section</b>: {{ activity.section }}<br/><br/>
                    {% endfor %}
                    <br/>
                    Please click this link to view the additional information/clarifications requested:
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/><br/>
                    Thank you.
                    {% endblock %}
                """
            }
        )

        EmailTemplate.objects.update_or_create(
            name='tpm/visit/approve_report_tpm',
            defaults={
                'description': 'Report was approved. Notify TPM.',
                'subject': 'UNICEF approved Final report for the Monitoring/Verification Visit '
                           '{{ visit.reference_number }}',

                'content': strip_text("""
                    UNICEF approved final report submited for the Monitoring/Verification visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}.
                    Please refer below for additional information.

                    {% for activity in visit.tpm_activities %}
                    PD/SSFA/ToR: {{ activity.intervention}}
                    CP Output: {{ activity.cp_output }}
                    Location: {{ activity.locations }}
                    Section: {{ activity.section }}

                    {% endfor %}

                    Please click this link for additional information: {{ visit.object_url }}
                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ recipient }},<br/>
                    <br/>
                    UNICEF approved final report submited for the Monitoring/Verification visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
                    <br/>
                    Please refer below for additional information.<br/>
                    <br/>
                    {% for activity in visit.tpm_activities %}
                    <b>PD/SSFA/ToR</b>: {{ activity.intervention }}<br/>
                    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
                    <b>Locations</b>: {{ activity.locations }}</br>
                    <b>Section</b>: {{ activity.section }}<br/><br/>
                    {% endfor %}
                    <br/>
                    Please click this link for additional information:
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/><br/>
                    Thank you.
                    {% endblock %}
                """
            }
        )

        EmailTemplate.objects.update_or_create(
            name='tpm/visit/approve_report',
            defaults={
                'description': 'Report was approved. Notify UNICEF focal points.',
                'subject': 'UNICEF approved Final report for the Monitoring/Verification Visit '
                           '{{ visit.reference_number }}',

                'content': strip_text("""
                    UNICEF approved final report submited for the Monitoring/Verification visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}.
                    Please refer below for additional information.

                    {% for activity in visit.tpm_activities %}
                    PD/SSFA/ToR: {{ activity.intervention}}
                    CP Output: {{ activity.cp_output }}
                    Location: {{ activity.locations }}
                    Section: {{ activity.section }}
                    {% endfor %}

                    Please click this link for additional information: {{ visit.object_url }}
                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ recipient }},<br/>
                    <br/>
                    UNICEF approved final report submited for the Monitoring/Verification visit to
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
                    <br/>
                    Please refer below for additional information.<br/>
                    <br/>
                    {% for activity in visit.tpm_activities %}
                    <b>PD/SSFA/ToR</b>: {{ activity.intervention }}<br/>
                    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
                    <b>Locations</b>: {{ activity.locations }}</br>
                    <b>Section</b>: {{ activity.section }}<br/><br/>
                    {% endfor %}
                    <br/>
                    Please click this link for additional information:
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/><br/>
                    Thank you.
                    {% endblock %}
                """
            }
        )

        EmailTemplate.objects.update_or_create(
            name='tpm/visit/action_point_assigned',
            defaults={
                'description': 'Action point assigned to visit. Person responsible should be notified.',
                'subject': '[eTools] ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',

                'content': strip_text("""
                    Dear {{ action_point.person_responsible.first_name }},

                    {{ action_point.author.get_full_name }} has assigned you an action point related to
                    Monitoring/Verification Visit {{ visit.reference_number }}.

                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}.
                    Please refer below for additional information.

                    {% for activity in visit.tpm_activities %}
                    PD/SSFA/ToR: {{ activity.intervention}}
                    CP Output: {{ activity.cp_output }}
                    Location: {{ activity.locations }}
                    Section: {{ activity.section }}
                    {% endfor %}

                    Please click this link for additional information: {{ visit.object_url }}
                    Thank you.
                """),

                'html_content': """
                    {% extends "email-templates/base" %}

                    {% block content %}
                    Dear {{ action_point.person_responsible.first_name }},<br/>
                    <br/>
                    <b>{{ action_point.author.get_full_name }}</b> has assigned you an action point related to
                    Monitoring/Verification Visit {{ visit.reference_number }}.<br/>
                    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
                    <br/>
                    Please refer below for additional information.<br/>
                    <br/>
                    {% for activity in visit.tpm_activities %}
                    <b>PD/SSFA/ToR</b>: {{ activity.intervention }}<br/>
                    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
                    <b>Locations</b>: {{ activity.locations }}</br>
                    <b>Section</b>: {{ activity.section }}<br/><br/>
                    {% endfor %}

                    Please click this link for additional information:
                    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/><br/>
                    Thank you.
                    {% endblock %}
                """
            }
        )

        # Action Points Module
        EmailTemplate.objects.update_or_create(
            name='action_points/action_point/assigned',
            defaults={
                'description': 'Action point assigned/reassigned',
                'subject': '[eTools] ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',

                'content': """
                Dear {{ recipient }},

                {{ action_point.assigned_by }} has assigned you an action point related to:
                Implementing Partner: {{ action_point.implementing_partner }}
                Description: {{ action_point.description }}

                Link: {{ action_point.object_url }}
                """,

                'html_content': """
                {% extends "email-templates/base" %}

                {% block content %}
                Dear {{ recipient }},<br/><br/>

                {{ action_point.assigned_by }} has assigned you an action point related to:<br/>
                Implementing Partner: {{ action_point.implementing_partner }}<br/>
                Description: {{ action_point.description }}<br/>
                Link: <a href="{{ action_point.object_url }}">{{ action_point.reference_number }}</a>
                {% endblock %}
                """
            }
        )
        EmailTemplate.objects.update_or_create(
            name='action_points/action_point/completed',
            defaults={
                'description': 'Action point completed',
                'subject': '[eTools] ACTION POINT CLOSURE to {{ action_point.person_responsible }}',

                'content': """
                Dear {{ recipient }},

                {{ action_point.person_responsible }} has closed the following action point:
                Reference Number: {{ action_point.reference_number }}
                Description: {{ action_point.description }}
                Due Date: {{ action_point.due_date }}
                Link: {{ action_point.object_url }}
                """,

                'html_content': """
                {% extends "email-templates/base" %}

                {% block content %}
                Dear {{ recipient }},<br/><br/>

                {{ action_point.person_responsible }} has closed the following action point:<br/>
                Reference Number: {{ action_point.reference_number }}<br/>
                Description: {{ action_point.description }}<br/>
                Due Date: {{ action_point.due_date }}<br/>
                Link: <a href="{{ action_point.object_url }}">{{ action_point.reference_number }}</a>
                {% endblock %}
                """
            }
        )

        logger.info(u'Command finished')
