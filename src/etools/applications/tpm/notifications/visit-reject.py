from unicef_notification.utils import strip_text

name = 'tpm/visit/reject'
defaults = {
    'description': 'TPM rejected visit. Notify focal points.',
    "subject": "{{ visit.tpm_partner }} has rejected the Monitoring/Verification Visit Request "
    "{{ visit.reference_number }}",
    "content": strip_text("""
    Dear {{ recipient }},

    TPM {{ visit.tpm_partner }} has rejected your request for a Monitoring/Verifcation visit to
    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}

    Please click this link for additional information and reason for rejection {{ visit.object_url }}

    Thank you.
    """),
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/>
    <br/>
    TPM <b>{{ visit.tpm_partner }}</b> has rejected your request for a Monitoring/Verifcation visit to
    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
    <br/><br/>
    Please click this link for additional information and reason for rejection
    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/>
    <br/>
    Thank you.
    {% endblock %}
    """,
}
