from unicef_notification.utils import strip_text

name = 'action_points/action_point/action_point-available-for-verification'
defaults = {
    'description': 'Action point available for verification',
    'subject': '[eTools] ACTION POINT available for verification',

    'content': strip_text("""
    Dear {{ recipient }},

    You was assigned as a verifier to an action point {% if action_point.partner %}related to:
    Implementing Partner: {{ action_point.partner }}{% endif %}
    Description: {{ action_point.description }}

    Link: {{ action_point.object_url }}
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/><br/>

    You was assigned as a verifier to an action point {% if action_point.partner %}related to:
    <br/>
    Implementing Partner: {{ action_point.partner }}{% endif %}<br/>
    Description: {{ action_point.description }}<br/>
    Link: <a href="{{ action_point.object_url }}">{{ action_point.reference_number }}</a>
    {% endblock %}
    """
}
