from unicef_notification.utils import strip_text

name = 'users/amp/role-update'
defaults = {
    'description': 'User role update',
    'subject': '[eTools] User role update for {{ user_full_name }}',

    'content': strip_text("""
    Dear {{  user_full_name }},

    Your role in UNICEF's Access Management Portal has been updated.
    You now have access to:
    {% for realm in active_realms %}
        {{ realm.organization__name }} organization in {{ realm.country__name }} with the role of {{ realm.group__name }} <br/>
    {% endfor %}
    Kind regards,
    UNICEF
    Please note that this is an automatically generated email. Responses are not monitored and cannot be replied to.</p>
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ user_full_name }}, <br/>

    Your role in UNICEF's Access Management Portal has been updated.
    You now have access to: <br/><br/>
    {% for realm in active_realms %}
    <b>{{ realm.organization__name }}</b> organization in <b>{{ realm.country__name }}</b> with the role of <b>{{ realm.group__name }}</b> <br/><br/>
    {% endfor %}
    <br/>
    Kind regards,</br>
    UNICEF<br/>
    <p>Please note that this is an automatically generated email. Responses are not monitored and cannot be replied to.</p>
    {% endblock content %}
    """
}
