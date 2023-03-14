name = "partners/intervention/partner_unlocked"
defaults = {
    "description": "Partner Unlocked PD",
    "subject": "[eTools] Partner Unlocked PD",
    "content": """
    Dear Partner,

    PD {{reference_number}} has been unlocked by UNICEF.

    {{pd_link}}

    This action cancelled all the previous approvals and returned the PD to the Development phase.
    Please complete all the desired/recommended changes and then click "accept as final".

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Partner,<br /><br />

    PD {{reference_number}} has been unlocked by UNICEF.<br />

    {{pd_link}}<br />

    This action cancelled all the previous approvals and returned the PD to the Development phase.
    Please complete all the desired/recommended changes and then click "accept as final".<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
