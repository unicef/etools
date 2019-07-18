name = 'action_points/action_point/overdue'
defaults = {
    'description': 'Action point overdue',
    'subject': '[eTools] ACTION POINT OVERDUE',

    'content': """
    Dear {{ action_point.assigned_to.get_full_name }},

    The due date for the action point that was assigned to you has passed
    without completion of the action. Please access this page
    {{ url }} to complete the action point.
    """,

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ action_point.assigned_to.get_full_name }},
    <br /><br />
    The due date for the action point that was assigned to you has passed
    without completion of the action. Please access
    <a href="{{ url }}">this page</a> to complete the action point.
    {% endblock %}
    """
}
