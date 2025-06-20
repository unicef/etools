name = "governments/gdd/send_to_unicef"
defaults = {
    "description": "GPD sent to UNICEF",
    "subject": "[eTools] GPD sent to UNICEF",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been sent to UNICEF.
    Please follow the link below to start the GPD development.

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been sent to UNICEF.<br />
    Please follow the link below to start the GPD development.<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
