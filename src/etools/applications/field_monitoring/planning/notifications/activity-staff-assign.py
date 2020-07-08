from unicef_notification.utils import strip_text

name = 'fm/activity/staff-assign'
defaults = {
    'description': 'FM Activity assigned. Staff should be notified.',
    'subject': '[FM Portal] Monitoring Activity Assigned',

    'content': strip_text("""
    Dear colleague,

    A Field Monitoring activity has been assigned to you in eTools.

    Please click {{ activity.object_url }} to access your assigned activity.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear colleague,<br/>
    <br/>
    A Field Monitoring activity has been assigned to you in eTools.<br/>
    <br/>
    Please click <a href="{{ activity.object_url }}">{{ activity.object_url }}</a> to access your assigned activity.<br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
