name = "governments/gdd/unicef_accepted"
defaults = {
    "description": "UNICEF Accepted GPD",
    "subject": "[eTools] UNICEF Accepted GPD",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been accepted by UNICEF

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been accepted by UNICEF

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
