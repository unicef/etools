from unicef_notification.utils import strip_text

name = 'organisations/staff_member/invite'
defaults = {
    'description': 'The email that is sent to partner staff member when he have been '
    'registered in the system.',
    'subject': 'eTools {% if environment %}{{ environment }} {% endif %}- Invitation',

    'content': strip_text("""
    Dear Colleague,

    You have been invited to the eTools. To get access to our system follow link.

    {{ login_link }}

    eTools Team
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block title %}eTools {% if environment %}{{ environment }} {% endif %}- Invitation{% endblock %}

    {% block content %}
    <p>Dear Colleague,</p>

    <p>
    You have been invited to the <b>eTools</b>.
    To get access to our system follow <a href="{{ login_link }}">link</a>.
    </p>

    <p style="text-align:right">eTools Team</p>
    {% endblock %}
    """
}
