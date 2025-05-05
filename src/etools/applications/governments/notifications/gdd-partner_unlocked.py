name = "governments/gdd/partner_unlocked"
defaults = {
    "description": "Partner Unlocked GPD",
    "subject": "[eTools] Partner Unlocked GPD",
    "content": """
    Dear Partner,

    GPD {{reference_number}} has been unlocked by UNICEF.

    {{gdd_link}}

    This action cancelled all the previous approvals and returned the GPD to the Development phase.
    Please complete all the desired/recommended changes and then click "accept as final".

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Partner,<br /><br />

    GPD {{reference_number}} has been unlocked by UNICEF.<br />

    {{gdd_link}}<br />

    This action cancelled all the previous approvals and returned the GPD to the Development phase.
    Please complete all the desired/recommended changes and then click "accept as final".<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
