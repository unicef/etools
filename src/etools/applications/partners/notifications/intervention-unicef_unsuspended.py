name = "partners/intervention/unicef_unsuspended"
defaults = {
    "description": "UNICEF has unsuspended a PD",
    "subject": "[eTools] UNICEF has unsuspended a PD",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been unsuspended by UNICEF.

    Please reach out to the PD focal point for details on the PD.

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been unsuspended by UNICEF.<br />

    Please reach out to the PD focal point for details on the PD.<br />

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
