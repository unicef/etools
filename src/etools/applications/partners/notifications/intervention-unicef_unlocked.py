name = "partners/intervention/unicef_unlocked"
defaults = {
    "description": "UNICEF Unlocked PD",
    "subject": "[eTools] UNICEF Unlocked PD",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been unlocked by UNICEF,
    The previously accepted PD has been moved back to Development and will need to be accepted again after desired
    modifications have been completed.

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been unlocked by UNICEF,<br />
    The previously accepted PD has been moved back to Development and will need to be accepted again after desired
    modifications have been completed.

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
