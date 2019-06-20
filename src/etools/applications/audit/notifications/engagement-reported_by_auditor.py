from unicef_notification.utils import strip_text

name = 'audit/engagement/reported_by_auditor'
defaults = {
    'description': 'Email that send when auditor fill engagement\'s report.',
    'subject': '{{ engagement.auditor_firm }} has completed the final report for '
    '{{ engagement.engagement_type }}, {{ engagement.reference_number }}',

    'content': strip_text("""
    Dear Audit Focal Point,

    {{ engagement.auditor_firm }} has completed the final report for {{ engagement.engagement_type }}.
    Please refer below for additional information.

    Engagement Type: {{ engagement.engagement_type }}
    Partner: {{ engagement.partner }}

    Please click this link to view the final report: {{ engagement.object_url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Audit Focal Point,<br/><br/>

    {{ engagement.auditor_firm }} has completed the final report for {{ engagement.engagement_type }}.
    Please refer below for additional information.<br/><br/>

    Engagement Type: {{ engagement.engagement_type }}<br/>
    Partner: {{ engagement.partner }}<br/><br/>

    Please click <a href="{{ engagement.object_url }}">this link</a> to view the final report.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
