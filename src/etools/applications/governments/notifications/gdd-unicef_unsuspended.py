name = "governments/gdd/unicef_unsuspended"
defaults = {
    "description": "UNICEF has unsuspended a GPD",
    "subject": "[eTools] UNICEF has unsuspended a GPD",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been unsuspended by UNICEF.

    Please reach out to the GPD focal point for details on the GPD.

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been unsuspended by UNICEF.<br />

    Please reach out to the GPD focal point for details on the GPD.<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
