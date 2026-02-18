from unicef_notification.utils import strip_text

name = 'fm/activity/send-report'
defaults = {
    'description': 'FM Activity report sent by email.',
    'subject': '[FM Portal] Field Monitoring Report {{ activity.reference_number }}',

    'content': strip_text("""
    Dear,
    {% if message %}

        {{ message }}

    {% endif %}
    Please find attached the Field Monitoring Report for {{ activity.reference_number }}.

    You can view the report online at {{ activity.object_url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear,<br/>
    <br/>
    {% if message %}
        {{ message }}<br/>
        <br/>
    {% endif %}
    Please find attached the Field Monitoring Report for {{ activity.reference_number }}.<br/>
    <br/>
    You can view the report online at <a href="{{ activity.object_url }}">{{ activity.object_url }}</a><br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
