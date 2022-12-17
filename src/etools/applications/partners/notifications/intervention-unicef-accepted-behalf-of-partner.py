name = "partners/intervention/unicef_accepted_behalf_of_partner"
defaults = {
    "description": "UNICEF Accepted PD on behalf of Partner",
    "subject": "[eTools] UNICEF Accepted the PD on behalf of Partner",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been accepted by UNICEF on behalf of Partner

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been accepted by UNICEF on behalf of Partner

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
