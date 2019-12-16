name = 'partners/hact_updated'
defaults = {
    'description': 'HACT values have changed from previous sync',
    'subject': 'eTools {{environment}} - New minimum assurance activities required',
    'content': """
    Dear Audit Focal Point,

    The implementing partner(s) listed below require a new assurance activity.
    Please review the assurance plan and schedule the assurance activity accordingly for this year.
    If the assurance activity has been already completed, no further action is required.

    {% for vendor_number, partner, updated in partners %}
    {{vendor_number}} {{partner}} New: {{updated}}
    {% endfor %}

    Please note that this is an automated message and replies to this address not monitored.
    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Audit Focal Point,<br/><br/>

    The implementing partner(s) listed below require a new assurance activity. <br/>
    Please review the assurance plan and schedule the assurance activity accordingly for this year.<br/>
    If the assurance activity has been already completed, no further action is required.<br/><br/>
    <ul>
    {% for vendor_number, partner, updated in partners %}
    <li>{{vendor_number}} {{partner}} New: {{updated}}</li>
    {% endfor %}
    </ul>
    <br/>

    Please note that this is an automated message and replies to this address not monitored.<br/>
    {% endblock %}
    """
}
