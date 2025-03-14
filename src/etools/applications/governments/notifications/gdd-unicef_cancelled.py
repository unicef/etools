name = "governments/gdd/unicef_cancelled"
defaults = {
    "description": "UNICEF Cancelled GDD",
    "subject": "[eTools] GDD was cancelled",
    "content": """
    Dear Colleague,

    GDD {{reference_number}} has been cancelled by UNICEF.

    Please reach out to the GDD focal point for details on the GDD.

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GDD {{reference_number}} has been cancelled by UNICEF.<br />

    Please reach out to the GDD focal point for details on the GDD.<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
