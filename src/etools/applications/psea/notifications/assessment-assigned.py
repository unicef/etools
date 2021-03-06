name = 'psea/assessment/assigned'
defaults = {
    'description': 'PSEA Assessment Assigned.',
    'subject': 'PSEA Assessment Assigned for {{ partner_name }}',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment has been assigned for the following Partner:

    Vendor Number: {{ partner_vendor_number }}

    Vendor Name: {{ partner_name }}

    Please visit {{ url }} to complete the report.

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleagues,<br/><br/>

    Please note that a PSEA assessment has been assigned for the following Partner:<br/><br/>

    Vendor Number: {{ partner_vendor_number }}<br/><br/>

    Vendor Name: {{ partner_name }}<br/><br/>

    Please click <a href="{{ url }}">this link</a> to complete the report.<br/><br/>

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.
    {% endblock %}
    """
}
