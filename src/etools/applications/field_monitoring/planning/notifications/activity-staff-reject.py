from unicef_notification.utils import strip_text

name = 'fm/activity/staff-reject'
defaults = {
    'description': 'FM Activity rejected by Staff. Person responsible should be notified.',
    'subject': '[FM Portal] Request for more information on the Final report for the Monitoring/Verification activity {{ activity.reference_number }}',

    'content': strip_text("""
    Dear {{ recipient }},

    UNICEF has requested additional information on the final report submited for the Monitoring/Verification visit to {{ activity.location name }}, {{ activity.reference_number }}.

    Please click {{ activity.object_url }} to view the additional information/clarifications requested.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/>
    <br/>
    UNICEF has requested additional information on the final report submited for the Monitoring/Verification visit to {{ activity.location name }}, {{ activity.reference_number }}.<br/>
    <br/>
    Please click <a href="{{ activity.object_url }}">{{ activity.object_url }}</a> to view the additional information/clarifications requested.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
