from unicef_notification.utils import strip_text

name = 'audit/staff_member/invite'
defaults = {
    'description': 'Invite staff member to auditor portal',
    'subject': 'UNICEF Auditor Portal Access',

    'content': strip_text("""
    Dear {{ staff_member }},

    UNICEF has assigned a {{ engagement.engagement_type }} to you.
    Please click link to login or sign up to gain access to the UNICEF Financial Assurance Module.

    {{ login_link }}

    eTools Team
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block title %}UNICEF Auditor Portal Access{% endblock %}

    {% block content %}

    <p>Dear {{ staff_member }},</p>

    <p>UNICEF has assigned a {{ engagement.engagement_type }} to you.
    Please click link to login or sign up to gain access to the UNICEF Financial Assurance Module.</p>

    <a href="{{ login_link }}">link</a>

    <p style="text-align:right">eTools Team</p>
    {% endblock %}
    """
}
