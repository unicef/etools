name = "governments/gdd/unicef_accepted_reviewed"
defaults = {
    "description": "UNICEF Accepted and Reviewed GDD",
    "subject": "[eTools] UNICEF Accepted and Reviewed GDD",
    "content": """
    Dear Colleague,

    GDD {{reference_number}} has been accepted and reviewed by UNICEF

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GDD {{reference_number}} has been accepted and reviewed by UNICEF

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
