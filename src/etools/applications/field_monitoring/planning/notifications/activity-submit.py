from unicef_notification.utils import strip_text

name = 'fm/activity/submit'
defaults = {
    'description': 'FM Activity submitted by TPM. PME should be notified.',
    'subject': '[FM Portal] {{ activity.vendor_name }} has submitted the final report for {{ activity.reference_number }}',

    'content': strip_text("""
    Dear {{ recipient }},

    {{ activity.vendor_name }} has submitted the final report for the Monitoring/Verification visit.

    Please click {{ activity.object_url }}  to view the final report and take the appropriate action.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/>
    <br/>
    {{ activity.vendor_name }} has submitted the final report for the Monitoring/Verification visit.<br/>
    <br/>
    Please click <a href="{{ activity.object_url }}">{{ activity.object_url }}</a> to view the final report and take the appropriate action.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
