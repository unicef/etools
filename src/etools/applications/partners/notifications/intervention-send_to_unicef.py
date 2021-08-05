name = "partners/intervention/send_to_unicef"
defaults = {
    "description": "Send PD to UNICEF",
    "subject": "[eTools] PD Open for Updates by UNICEF",
    "content": """
    Dear Colleague,

    PD {{reference_number}} now with {{ partner_name }}

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} now with {{ partner_name }}

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
