name = "partners/intervention/unicef_sent_for_review"
defaults = {
    "description": "UNICEF Sent PD for Review",
    "subject": "[eTools] PD was sent for review",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been sent for review by UNICEF budget owner: {{budget_owner_name}}

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been sent for review by UNICEF budget owner: {{budget_owner_name}}

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
