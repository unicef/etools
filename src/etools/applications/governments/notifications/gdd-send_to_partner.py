name = "governments/gdd/send_to_partner"
defaults = {
    "description": "GPD sent to Partner",
    "subject": "[eTools] GPD sent to Partner",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been sent to you, {{ partner_name }}.
    Please follow the link below to start the GPD development.

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been sent to you, {{ partner_name }}.<br />
    Please follow the link below to start the GPD development.<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
