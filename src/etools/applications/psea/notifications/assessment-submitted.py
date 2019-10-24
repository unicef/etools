from unicef_notification.utils import strip_text

# Receiver: Vendor Master Team, GSSC

name = 'psea/assessment/submitted'
defaults = {
    'description': 'Email sent to focal points when PSEA assessment has been submitted by external vendor.',
    'subject': 'PSEA Assessment for {{ partner.name }}',

    'content': strip_text("""
    Dear Assessor,

    UNICEF is granting you access to the PSEA Module in eTools.
    Please refer below for additional information.

    Assessment Type: {{ assessment.assessment_type }}
    Partner: {{ partner.name }}

    Please click this link to complete the report: {{ url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Assessor,<br/><br/>

    UNICEF is granting you access to the PSEA Module in eTools.<br/>
    Please refer below for additional information.<br/><br/>

    Assessment Type: {{ assessment.assessment_type }}<br/>
    Partner: {{ partner.name }}<br/><br/>

    Please click <a href="{{ url }}">this link</a> to complete the report.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
