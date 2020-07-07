from unicef_notification.utils import strip_text

name = 'fm/activity/rejected-responsible'
defaults = {
    'description': 'FM Activity assigned. Staff should be notified.',
    'subject': '[FM Portal] Request for more information on the Final report for the Monitoring/Verification activity {{ reference_number }}',

    'content': strip_text("""
    Dear colleague,

    UNICEF has requested additional information on the final report submited for the Monitoring/Verification visit to {{ location name }}, {{ reference_number }}.

    Please click {{ object_url }} to view the additional information/clarifications requested.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear colleague,<br/>
    <br/>
    A Field Monitoring activity has been assigned to you in eTools.<br/>
    <br/>
    Please click <a href="{{ object_url }}">{{ object_url }}</a> to access your assigned activity.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
