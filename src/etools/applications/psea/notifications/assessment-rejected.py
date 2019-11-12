name = 'psea/assessment/rejected'
defaults = {
    'description': 'PSEA Assessment Rejected.',
    'subject': 'PSEA Assessment Rejected for {{ partner_name }}',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment has been rejected for the following Partner:

    Vendor Number: {{ partner_vendor_number }}

    Vendor Name: {{ partner_name }}

    Date of Assessment: {{ assessment_date }}

    Comment: {{ rejected_comment }}

    Please visit {{ url }} to complete the report.

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleagues,<br/><br/>

    Please note that a PSEA assessment has been rejected for the following Partner:<br/><br/>

    Vendor Number: {{ partner_vendor_number }}<br/><br/>

    Vendor Name: {{ partner_name }}<br/><br/>

    Date of Assessment: {{ assessment_date }}<br/><br/>

    Comment: {{ rejected_comment }}<br/><br/>

    Please click <a href="{{ url }}">this link</a> to complete the report.<br/><br/>

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.
    {% endblock %}
    """
}
