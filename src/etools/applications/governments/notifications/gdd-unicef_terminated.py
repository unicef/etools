name = "governments/gdd/unicef_terminated"
defaults = {
    "description": "UNICEF Terminated GPD",
    "subject": "[eTools] UNICEF Terminated GPD",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been terminated by UNICEF.

    Please reach out to the GPD focal point for details on the GPD.

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been terminated by UNICEF. <br />

    Please reach out to the GPD focal point for details on the GPD.<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
