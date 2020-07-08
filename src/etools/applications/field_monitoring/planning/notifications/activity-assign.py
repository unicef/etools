from unicef_notification.utils import strip_text

name = 'fm/activity/assign'
defaults = {
    'description': 'FM Activity assigned. Team members, and person responsible should be notified.',
    'subject': '[FM Portal] Access to eTools Field Monitoring Module',

    'content': strip_text("""
    Dear {{ recipient }},

    UNICEF is granting you access to the Field Monitoring Module in eTools.

    Please click {{ activity.object_url }} to access your assigned activity.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/>
    <br/>
    UNICEF is granting you access to the Field Monitoring Module in eTools.<br/>
    <br/>
    Please click <a href="{{ activity.object_url }}">{{ activity.object_url }}</a> to access your assigned activity.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
