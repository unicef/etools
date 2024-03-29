name = "partners/intervention/send_to_unicef"
defaults = {
    "description": "PD sent to UNICEF",
    "subject": "[eTools] PD sent to UNICEF",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been sent to UNICEF.
    Please follow the link below to start the PD/SPD development.

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been sent to UNICEF.<br />
    Please follow the link below to start the PD/SPD development.<br />

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
