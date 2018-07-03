from unicef_notification.utils import strip_text

name = 'email_auth/token/login'
defaults = {
    'description': 'The email that is sent to user to login without password.',
    'subject': 'eTools Access Token',
    'content': strip_text("""
    Dear {{ recipient }},

    Please click on this link to sign in to eTools portal:

    {{ login_link }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block title %}eTools Access Token{% endblock %}

    {% block content %}
    <p>Dear {{ recipient }},</p>

    <p>Please click on <a href="{{ login_link }}">this link</a> to sign in to eTools portal.</p>

    <p>Thank you.</p>
    {% endblock %}
    """
}
