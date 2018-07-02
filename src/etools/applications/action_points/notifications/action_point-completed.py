name = 'action_points/action_point/completed'
defaults = {
    'description': 'Action point completed',
    'subject': '[eTools] ACTION POINT CLOSURE to {{ action_point.person_responsible }}',

    'content': """
    Dear {{ recipient }},

    {{ action_point.person_responsible }} has closed the following action point:
    Reference Number: {{ action_point.reference_number }}
    Description: {{ action_point.description }}
    Due Date: {{ action_point.due_date }}
    Link: {{ action_point.object_url }}
    """,

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/><br/>

    {{ action_point.person_responsible }} has closed the following action point:<br/>
    Reference Number: {{ action_point.reference_number }}<br/>
    Description: {{ action_point.description }}<br/>
    Due Date: {{ action_point.due_date }}<br/>
    Link: <a href="{{ action_point.object_url }}">{{ action_point.reference_number }}</a>
    {% endblock %}
    """
}
