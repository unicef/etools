name = "governments/gdd/unicef_pending_approval"
defaults = {
    "description": "UNICEF Pending Approval GPD",
    "subject": "[eTools] UNICEF Pending Approval GPD",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} is ready to be approved. Please download it at the following link and share it with the relevant authorized officers for pending approval:

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} is ready to be approved. Please download it at the following link and share it with the relevant authorized officers for pending approval:<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
