name = "governments/gdd/unicef_signature"
defaults = {
    "description": "UNICEF Signature GDD",
    "subject": "[eTools] UNICEF Signature GDD",
    "content": """
    Dear Colleague,

    GDD {{reference_number}} is ready to be signed. Please download it at the following link and share it with the relevant authorized officers for signature:

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GDD {{reference_number}} is ready to be signed. Please download it at the following link and share it with the relevant authorized officers for signature:<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
