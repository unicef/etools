name = "governments/gdd/partner_accepted"
defaults = {
    "description": "Partner Accepted GPD",
    "subject": "[eTools] Partner Accepted GPD",
    "content": """
    Dear Colleague,

    GPD {{reference_number}} has been accepted by {{ partner_name }}

    {{gdd_link}}

    Please note that a Regular GPD less than $100,000 should be finalized in 45 days and an GPD for Humanitarian response should be finalized in 15 days.

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GPD {{reference_number}} has been accepted by {{ partner_name }}

    {{gdd_link}}<br />

    Please note that a Regular GPD less than $100,000 should be finalized in 45 days and an GPD for Humanitarian response should be finalized in 15 days.<br/>

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
