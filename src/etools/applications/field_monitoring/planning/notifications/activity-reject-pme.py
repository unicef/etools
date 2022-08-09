from unicef_notification.utils import strip_text

name = 'fm/activity/reject-pme'
defaults = {
    'description': 'FM Activity rejected by PME. Visit Lead should be notified.',
    'subject': '[FM Portal] {{ activity.vendor_name }} has rejected the Monitoring/Verification Visit Request activity {{ activity.reference_number }}',

    'content': strip_text("""
    Dear {{ recipient }},

    {{ activity.vendor_name }} has rejected your request for a Monitoring/Verifcation activity to Implementing Partner {{ activity.location_name }}.

    Please click {{ activity.object_url }} for additional information and reason for rejection.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear colleague,<br/>
    <br/>
    {{ activity.vendor_name }} has rejected your request for a Monitoring/Verifcation activity to Implementing Partner {{ activity.location_name }}.<br/>
    <br/>
    Please click <a href="{{ activity.object_url }}">{{ activity.object_url }}</a> for additional information and reason for rejection.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
