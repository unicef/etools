name = 'action_points/action_point/completed'
defaults = {
    'description': 'Action point completed',
    'subject': '[eTools] ACTION POINT CLOSURE to {{ completed_by }}',

    'content': """
    Dear {{ recipient }},

    {{ completed_by }} has closed the following action point:
    Reference Number: {{ action_point.reference_number }}
    Description: {{ action_point.description }}
    Due Date: {{ action_point.due_date }}
    Link: {{ action_point.object_url }}
    """,

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/><br/>

    {{ completed_by }} has closed the following action point:<br/>
    Reference Number: {{ action_point.reference_number }}<br/>
    Description: {{ action_point.description }}<br/>
    Due Date: {{ action_point.due_date }}<br/>
    Link: <a href="{{ action_point.object_url }}">{{ action_point.reference_number }}</a>
    {% endblock %}
    """
}
