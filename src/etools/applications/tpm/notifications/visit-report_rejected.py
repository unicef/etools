from unicef_notification.utils import strip_text

name = 'tpm/visit/report_rejected'
defaults = {
    'description': 'Report was rejected. Notify TPM.',
    'subject': 'Request for more information on the Final report for the Monitoring/Verification Visit '
    '{{ visit.reference_number }}',

    'content': strip_text("""
    UNICEF has requested additional information on  the final report submited for
    the Monitoring/Verification visit to
    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} {{ visit.partners }}.
    Please refer below for additional information.

    {% for activity in visit.tpm_activities %}
    PD/SPD/ToR: {{ activity.intervention}}
    CP Output: {{ activity.cp_output }}
    Location: {{ activity.locations }}
    Section: {{ activity.section }}

    {% endfor %}

    Please click this link to view the additional information/clarifications requested:
    {{ visit.object_url }}
    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/>
    <br/>
    UNICEF has requested additional information on  the final report submited for
    the Monitoring/Verification visit to
    Implementing Partner{% if visit.multiple_tpm_activities %}s{% endif %} <b>{{ visit.partners }}</b>.
    <br/>
    Please refer below for additional information.<br/>
    <br/>
    {% for activity in visit.tpm_activities %}
    <b>PD/SPD/ToR</b>: {{ activity.intervention }}<br/>
    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
    <b>Locations</b>: {{ activity.locations }}</br>
    <b>Section</b>: {{ activity.section }}<br/><br/>
    {% endfor %}
    <br/>
    Please click this link to view the additional information/clarifications requested:
    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a><br/><br/>
    Thank you.
    {% endblock %}
    """
}
