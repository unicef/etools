name = 'psea/assessment/assigned_focal'
defaults = {
    'description': 'PSEA Assessment Assigned.',
    'subject': 'PSEA Assessment Assigned for {{ partner_name }}',
    'content': """
    Dear PSEA Assessment Focal Point,

    Please note that a PSEA assessment has been assigned for the following Partner:

    Vendor Number: {{ partner_vendor_number }}

    Vendor Name: {{ partner_name }}

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear PSEA Assessment Focal Point,<br /><br />

    Please note that a PSEA assessment has been assigned for the following Partner:<br /><br />

    Vendor Number: {{ partner_vendor_number }}<br /><br />

    Vendor Name: {{ partner_name }}<br /><br />

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.
    {% endblock %}
    """
}
