from unicef_notification.utils import strip_text

name = 'audit/engagement/submit_to_auditor'
defaults = {
    'description': 'Email that send to auditor when engagement have been created.',
    'subject': 'Access to eTools Financial Assurance Module',

    'content': strip_text("""
    Dear {{ staff_member }},

    UNICEF is granting you access to the Financial Assurance Module in eTools.
    Please refer below for additional information.

    Engagement Type: {{ engagement.engagement_type }}
    Partner: {{ engagement.partner }}

    Please click this link to complete the report: {{ engagement.object_url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ staff_member }},<br/><br/>

    UNICEF is granting you access to the Financial Assurance Module in eTools.<br/>
    Please refer below for additional information.<br/><br/>

    Engagement Type: {{ engagement.engagement_type }}<br/>
    Partner: {{ engagement.partner }}<br/><br/>

    Please click <a href="{{ engagement.object_url }}">this link</a> to complete the report.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
