from unicef_notification.utils import strip_text

name = 'tpm/visit/action_point_assigned'
defaults = {
    'description': 'Action point assigned to visit. Person responsible should be notified.',
    'subject': '[eTools] ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',

    'content': strip_text("""
    Dear {{ action_point.person_responsible }},

    {% with action_point.tpm_activity as activity %}
    {{ action_point.assigned_by }} has assigned you an action point related to
    Monitoring/Verification Visit {{ activity.tpm_visit.reference_number }}.

    Implementing Partner {{ activity.partner }}.
    Please refer below for additional information.

    PD/SPD/ToR: {{ activity.intervention}}
    CP Output: {{ activity.cp_output }}
    Location: {{ activity.locations }}
    Section: {{ activity.section }}

    Please click this link for additional information: {{ activity.tpm_visit.object_url }}
    {% endwith %}
    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ action_point.person_responsible }},<br/>
    <br/>
    {% with action_point.tpm_activity as activity %}
    <b>{{ action_point.assigned_by }}</b> has assigned you an action point related to
    Monitoring/Verification Visit {{ activity.tpm_visit.reference_number }}.<br/>
    Implementing Partner <b>{{ activity.partner }}</b>.
    <br/>
    Please refer below for additional information.<br/>
    <br/>
    <b>PD/SPD/ToR</b>: {{ activity.intervention }}<br/>
    <b>CP Output</b> {{ activity.cp_output|default:"unassigned" }}<br/>
    <b>Locations</b>: {{ activity.locations }}</br>
    <b>Section</b>: {{ activity.section }}<br/><br/>

    Please click this link for additional information:
    <a href="{{ activity.tpm_visit.object_url }}">{{activity.tpm_visit.reference_number}}</a><br/><br/>
    {% endwith %}
    Thank you.
    {% endblock %}
    """
}
