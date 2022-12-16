from unicef_notification.utils import strip_text

name = 'tpm/visit/report'
defaults = {
    'description': 'TPM finished with visit report.  Notify PME & focal points.',
    'subject': '{{ visit.tpm_partner }} has submited the final report for {{ visit.reference_number }}',

    'content': strip_text("""
    Dear {{ recipient }},

    {{ visit.tpm_partner }} has submitted the final report for the Monitoring/Verification
    visit{% if partnerships %} requested for {{ visit.interventions }}{% endif %}.
    Please refer below for additional information.

    {% for activity in visit.tpm_activities %}
    PD/SPD/ToR: {{ activity.intervention}}
    CP Output: {{ activity.cp_output }}
    Location: {{ activity.locations }}
    Section: {{ activity.section }}
    {% endfor %}

    Please click this link to view the final report: {{ visit.object_url }} and take
    the appropriate action
    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/>
    <br/>
    <b>{{ visit.tpm_partner }}</b> has submitted the final report for the Monitoring/Verification
    visit{% if partnerships %} requested for <b>{{ visit.interventions }}</b>{% endif %}.<br/>
    Please refer below for additional information.<br/>
    <br/>
    {% for activity in visit.tpm_activities %}
    <b>PD/SPD/ToR</b>: {{ activity.intervention }}<br/>
    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
    <b>Locations</b>: {{ activity.locations }}</br>
    <b>Section</b>: {{ activity.section }}<br/><br/>
    {% endfor %}
    <br/>
    Please click this link to view the final report:
    <a href="{{ visit.object_url }}">{{ visit.object_url }}</a> and take
    the appropriate action<br/><br/>
    Thank you.
    {% endblock %}
    """
}
