from unicef_notification.utils import strip_text

name = 'audit/staff_member/invite'
defaults = {
    'description': 'Invite staff member to auditor portal',
    'subject': 'UNICEF Auditor Portal Access',

    'content': strip_text("""
    Dear {{ staff_member }},

    UNICEF has assingned a {{ engagement.engagement_type }} to you.
    Please click link to gain access to the UNICEF Auditor Portal.

    {{ login_link }}

    eTools Team
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block title %}UNICEF Auditor Portal Access{% endblock %}

    {% block content %}

    <p>Dear {{ staff_member }},</p>

    <p>UNICEF has assingned a {{ engagement.engagement_type }} to you.
    Please click <a href="{{ login_link }}">link</a> to gain access to the UNICEF Auditor Portal.</p>

    <p style="text-align:right">eTools Team</p>
    {% endblock %}
    """
}
