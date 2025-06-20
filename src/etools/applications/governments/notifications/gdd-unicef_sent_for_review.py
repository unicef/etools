name = "governments/gdd/unicef_sent_for_review"
defaults = {
    "description": "UNICEF Sent GPD for Review",
    "subject": "[eTools] GPD was sent for review",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been sent for review by UNICEF budget owner: {{budget_owner_name}}

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been sent for review by UNICEF budget owner: {{budget_owner_name}}

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
