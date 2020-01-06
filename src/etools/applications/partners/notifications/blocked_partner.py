name = 'partners/blocked_partner'
defaults = {
    'description': 'UNICEF Partner Blocked',
    'subject': 'eTools {{environment}} - UNICEF Partner Blocked: {{partner_name}}',
    'content': """
    Dear Colleague,

    Please note that Partner {{partner_name}} has been blocked in VISION.
    At the same time the partner has a following PDs/SSFA that is either Signed, Active or Ended:
    {{pds}}

    Please discuss follow up actions with UNICEF Authorized Officer including SSFA/PCA Termination.

    Please note that this is an automated message and replies to this address not monitored.
    """,
    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br/><br/>

    Please note that Partner {{partner_name}} has been blocked in VISION.<br/>
    At the same time the partner has a following PDs/SSFA that is either Signed, Active or Ended:<br/>
    {{pds}}<br/>

    Please discuss follow up actions with UNICEF Authorized Officer including SSFA/PCA Termination.<br/>

    Please note that this is an automated message and replies to this address not monitored.<br/>
    {% endblock %}
    """
}
