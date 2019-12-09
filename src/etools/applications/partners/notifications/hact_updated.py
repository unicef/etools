name = 'partners/hact_updated'
defaults = {
    'description': 'HACT values have changed from previous sync',
    'subject': 'eTools {{environment}} - UNICEF HACT MR values changed',
    'content': """
    Dear Colleague,

    Please note that HACT MR has changed for following partners:
    {% for partner in partners %}
    {{partner}}
    {% endfor %}

    Please note that this is an automated message and replies to this address not monitored.
    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br/><br/>

    Please note that HACT MR has changed for following partners:<br/>
    <ul>
    {% for partner in partners %}
    <li>{{partner}}</li>
    {% endfor %}
    </ul>
    <br/>

    Please note that this is an automated message and replies to this address not monitored.<br/>
    {% endblock %}
    """
}
