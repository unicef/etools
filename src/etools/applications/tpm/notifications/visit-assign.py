from unicef_notification.utils import strip_text

name = 'tpm/visit/assign'
defaults = {
    'description': 'Visit assigned. TPM should be notified.',
    'subject': '[TPM Portal] TPM Visit Request for {{ visit.partners }}; {{ visit.reference_number }}',

    'content': strip_text("""
    Dear {{ visit.tpm_partner }},

    UNICEF is requesting a Monitoring/Verification Visit for {{ visit.partners }}.
    Please refer below for additional information.
    {% for activity in visit.tpm_activities %}
    PD/SPD/ToR: {{ activity.intervention }}
    CP Output {{ activity.cp_output }}, {{ activity.locations }}

    {% endfor %}
    Please click this link for additional information and documents related to the visit:
    {{ visit.object_url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ visit.tpm_partner }},<br/>
    <br/>
    UNICEF is requesting a Monitoring/Verification Visit for <b>{{ visit.partners }}</b>. <br/><br/>
    Please refer below for additional information.<br/><br/>
    {% for activity in visit.tpm_activities %}
    <b>PD/SPD/ToR</b>: {{ activity.intervention }}<br/>
    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
    <b>Locations</b>: {{ activity.locations }}</br>
    <b>Section</b>: {{ activity.section }}<br/><br/>
    {% endfor %}
    <br/>
    Please click this link for additional information and documents related to the visit:
    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/>
    <br/>
    Thank you.
    {% endblock %}
    """
}
