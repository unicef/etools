from unicef_notification.utils import strip_text

name = 'action_points/action_point/assigned'
defaults = {
    'description': 'Action point assigned/reassigned',
    'subject': '[eTools] ACTION POINT ASSIGNED to {{ action_point.person_responsible }}',

    'content': strip_text("""
    Dear {{ recipient }},

    {{ action_point.assigned_by }} has assigned you an action point {% if action_point.partner %}related to:
    Implementing Partner: {{ action_point.partner }}{% endif %}
    Description: {{ action_point.description }}

    Link: {{ action_point.object_url }}
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/><br/>

    {{ action_point.assigned_by }} has assigned you an action point {% if action_point.partner %}related to:
    <br/>
    Implementing Partner: {{ action_point.partner }}{% endif %}<br/>
    Description: {{ action_point.description }}<br/>
    Link: <a href="{{ action_point.object_url }}">{{ action_point.reference_number }}</a>
    {% endblock %}
    """
}
