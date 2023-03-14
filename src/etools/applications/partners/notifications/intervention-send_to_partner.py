name = "partners/intervention/send_to_partner"
defaults = {
    "description": "PD sent to Partner",
    "subject": "[eTools] PD sent to Partner",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been sent to you, {{ partner_name }}.
    Please follow the link below to start the PD/SPD development.

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been sent to you, {{ partner_name }}.<br />
    Please follow the link below to start the PD/SPD development.<br />

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
