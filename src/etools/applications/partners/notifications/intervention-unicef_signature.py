name = "partners/intervention/unicef_signature"
defaults = {
    "description": "UNICEF Signature PD",
    "subject": "[eTools] UNICEF Signature PD",
    "content": """
    Dear Colleague,

    PD {{reference_number}} is ready to be signed. Please download it at the following link and share it with the relevant authorized officers for signature:

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} is ready to be signed. Please download it at the following link and share it with the relevant authorized officers for signature:<br />

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
