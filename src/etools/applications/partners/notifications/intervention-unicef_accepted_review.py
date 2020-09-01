name = "partners/intervention/unicef_accepted_reviewed"
defaults = {
    "description": "UNICEF Accepted and Reviewed PD",
    "subject": "[eTools] UNICEF Accepted and Reviewed PD",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been accepted and reviewed by UNICEF

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been accepted and reviewed by UNICEF

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
