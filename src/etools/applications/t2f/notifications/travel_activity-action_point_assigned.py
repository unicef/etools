from unicef_notification.utils import strip_text

name = 't2f/travel_activity/action_point_assigned'
defaults = {
    'description': 'Action point status changed in trip to visit. Person responsible should be notified.',
    'subject': '[eTools] Trips: ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',
    'content': strip_text("""
    Dear {{ action_point.person_responsible }},

    {{ action_point.assigned_by }} has assigned you an action point related to
    Trips Activity {{action_point.object_url}}.

    Description {{action_point.description}}
    Due Date {{action_point.due_date}}
    Implementing Partner {{ activity.partner }}.
    Please refer below for additional information.

    Please click this link for additional information: {{ activity.tpm_visit.object_url }}
    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ action_point.person_responsible }},<br/>
    <br/>
    <b>{{ action_point.assigned_by }}</b> has assigned you an action point related to
    Trips Activity: {{action_point.object_url}}.<br/>
    <br/>
    Description: {{action_point.object_url}}.<br/>
    Due Date: <b>{{ activity.partner }}</b>.
    <br/>
    Please refer below for additional information.<br/>
    <br/>

    Please click this link for additional information:
    <a href="{{ activity.tpm_visit.object_url }}">{{activity.tpm_visit.reference_number}}</a><br/><br/>
    Thank you.
    {% endblock %}
    """
}
