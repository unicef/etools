name = "governments/gdd/unicef_accepted_behalf_of_partner"
defaults = {
    "description": "UNICEF Accepted GDD on behalf of Partner",
    "subject": "[eTools] UNICEF Accepted the GDD on behalf of Partner",
    "content": """
    Dear Colleague,

    GDD {{reference_number}} has been accepted by UNICEF on your behalf.

    Please reach out to the GDD focal point for details on the GDD.


    {{gdd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br /><br />

    GDD {{reference_number}} has been accepted by UNICEF on your behalf.<br />

    Please reach out to the GDD focal point for details on the GDD.<br />

    {{gdd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />

    {% endblock content %}
    """
}
