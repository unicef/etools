from unicef_notification.utils import strip_text

name = 'fm/activity/reject'
defaults = {
    'description': 'FM Activity rejected by TPM. PME should be notified.',
    'subject': '[FM Portal] {{ vendor_name }} has rejected the Monitoring/Verification Visit Request activity {{ reference_number }}',

    'content': strip_text("""
    Dear {{ recipient }},

    {{ vendor_name }} has rejected your request for a Monitoring/Verifcation activity to Implementing Partner {{ location_name }}.

    Please click {{ object_url }} for additional information and reason for rejection.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear colleague,<br/>
    <br/>
    {{ vendor_name }} has rejected your request for a Monitoring/Verifcation activity to Implementing Partner {{ location_name }}.<br/>
    <br/>
    Please click <a href="{{ object_url }}">{{ object_url }}</a> for additional information and reason for rejection.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
