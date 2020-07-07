from unicef_notification.utils import strip_text

name = 'fm/activity/submit'
defaults = {
    'description': 'FM Activity submitted by TPM. PME should be notified.',
    'subject': '[FM Portal] {{ vendor_name }} has submitted the final report for {{ reference_number }}',

    'content': strip_text("""
    Dear {{ recipient }},

    {{ vendor_name }} has submitted the final report for the Monitoring/Verification visit.

    Please click {{ object_url }}  to view the final report and take the appropriate action.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/>
    <br/>
    {{ vendor_name }} has submitted the final report for the Monitoring/Verification visit.<br/>
    <br/>
    Please click <a href="{{ object_url }}">{{ object_url }}</a> to view the final report and take the appropriate action.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
