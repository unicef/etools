name = 'psea/assessment/final'
defaults = {
    'description': 'PSEA Assessment Final.',
    'subject': 'PSEA Assessment for {{ partner_name }}',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment was completed for the following Partner:

    Vendor Number: {{ partner_vendor_number }}

    Vendor Name: {{ partner_name }}
    PSEA Assessment Type: {{ assessment_type }}

    Reason for country-level INGO assessment (if different from INGO parent): {{ assessment_ingo_reason }}

    SEA Risk Rating: {{ overall_rating }}

    Date of Assessment: {{ assessment_date }}

    UNICEF Focal Points: {{ focal_points }}

    Please update the Vendor Master Data in VISION accordingly

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleagues,<br /><br />

    Please note that a PSEA assessment was completed for the following Partner:  <br /><br />

    Vendor Number: {{ partner_vendor_number }} <br /><br />

    Vendor Name: {{ partner_name }} <br /><br />

    PSEA Assessment Type: {{ assessment_type }} <br /><br />

    Reason for country-level INGO assessment (if different from INGO parent): {{ assessment_ingo_reason }} <br /><br />

    SEA Risk Rating: {{ overall_rating }} <br /><br />

    Date of Assessment: {{ assessment_date }}  <br /><br />

    UNICEF Focal Points: {{ focal_points }} <br /><br />

    Please update the Vendor Master Data in VISION accordingly  <br />
    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.
    {% endblock %}
    """
}
