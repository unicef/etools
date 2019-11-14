name = 'psea/assessment/submitted'
defaults = {
    'description': 'Email sent to focal points when PSEA assessment has been submitted by external vendor.',
    'subject': 'PSEA Assessment Submitted: {{ partner_name }}',

    'content': """
    Dear Colleague,

    Please note that a PSEA assessment for the following partner has been submitted:

    Vendor Number: {{ partner_vendor_number }}

    Vendor Name: {{ partner_name }}

    Assessor: {{ assessor }}

    Please visit {{ url }} to finalize the report.

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    Please note that a PSEA assessment for the following partner has been submitted:<br /><br />

    Vendor Number: {{ partner_vendor_number }}<br /><br />

    Vendor Name: {{ partner_name }}<br /><br />

    Assessor: {{ assessor }}<br /><br />

    Please click <a href="{{ url }}">this link</a> to finalize the report.<br /><br />

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.
    {% endblock %}
    """
}
