from unicef_notification.utils import strip_text

name = 'psea/assessment/action_point_assigned'
defaults = {
    'description': 'PSEA Assessment action point was assigned',
    'subject': '[eTools] ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',

    'content': strip_text("""
    Dear {{ action_point.person_responsible }},

    {{ action_point.assigned_by }} has assigned you an action point.

    PSEA Assessment Reference Number: {{ action_point.psea_assessment.reference_number }}
    Due Date: {{ action_point.due_date }}
    Link: {{ action_point.psea_assessment.object_url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ action_point.person_responsible }},<br/><br/>

    {{ action_point.assigned_by }} has assigned you an action point. <br/><br/>

    PSEA Assessment Reference Number: {{ action_point.psea_assessment.reference_number }}<br />
    Due Date: {{ action_point.due_date }}<br/>
    Link: <a href="{{ action_point.psea_assessment.object_url }}">click here</a><br/><br/>

    Thank you.
    {% endblock %}
    """
}
