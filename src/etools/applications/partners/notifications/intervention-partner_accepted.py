name = "partners/intervention/partner_accepted"
defaults = {
    "description": "Partner Accepted PD",
    "subject": "[eTools] Partner Accepted PD",
    "content": """
    Dear Colleague,

    PD {{reference_number}} has been accepted by {{ partner_name }}

    {{pd_link}}

    Please note that a Regular PD/SPD less than $100,000 should be finalized in 45 days and an SPD for Humanitarian response should be finalized in 15 days.

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    PD {{reference_number}} has been accepted by {{ partner_name }}

    {{pd_link}}<br />

    Please note that a Regular PD/SPD less than $100,000 should be finalized in 45 days and an SPD for Humanitarian response should be finalized in 15 days.<br/>

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
