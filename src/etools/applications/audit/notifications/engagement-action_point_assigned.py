from unicef_notification.utils import strip_text

name = 'audit/engagement/action_point_assigned'
defaults = {
    'description': 'Engagement action point was assigned',
    'subject': '[eTools] ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',

    'content': strip_text("""
    Dear {{ action_point.person_responsible }},

    {{ action_point.assigned_by }} has assigned you an action point.

    Engagement ID: {{ action_point.engagement.reference_number }}
    Due Date: {{ action_point.due_date }}
    Link: {{ action_point.engagement.object_url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ action_point.person_responsible }},<br/><br/>

    {{ action_point.assigned_by }} has assigned you an action point. <br/><br/>

    Engagement ID: {{ action_point.engagement.reference_number }}<br/>
    Due Date: {{ action_point.due_date }}<br/>
    Link: <a href="{{ action_point.engagement.object_url }}">click here</a><br/><br/>

    Thank you.
    {% endblock %}
    """
}
