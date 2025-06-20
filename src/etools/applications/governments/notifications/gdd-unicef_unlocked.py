name = "governments/gdd/unicef_unlocked"
defaults = {
    "description": "UNICEF Unlocked GPD",
    "subject": "[eTools] UNICEF Unlocked GPD",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been unlocked by UNICEF,
    The previously accepted GPD has been moved back to Development and will need to be accepted again after desired
    modifications have been completed.

    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been unlocked by UNICEF,<br />
    The previously accepted GPD has been moved back to Development and will need to be accepted again after desired
    modifications have been completed.

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
