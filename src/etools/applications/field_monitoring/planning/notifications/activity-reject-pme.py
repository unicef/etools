from unicef_notification.utils import strip_text

name = 'fm/activity/reject-pme'
defaults = {
    'description': 'Monitoring Visit Report was rejected by the PME. The visit lead should be notified.',
    'subject': '[eTools FM Module] PME has rejected the report for {{ activity.reference_number }}',

    'content': strip_text("""
    Dear colleague,

    The PME has rejected the Monitoring Visit Report that was submitted for FM Visit: {{ activity.reference_number }}'

    Please go to {{ activity.object_url }} for additional information and reason for rejection.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear colleague,<br/>
    <br/>
    The PME has rejected the Monitoring Visit Report that was submitted for FM Visit: {{ activity.reference_number }}<br/>
    <br/>
    Please go to <a href="{{ activity.object_url }}">{{ activity.object_url }}</a> for additional information and reason for rejection.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
