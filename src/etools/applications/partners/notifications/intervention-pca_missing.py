name = "partners/intervention/pca_missing"
defaults = {
    "description": "New PCA Required",
    "subject": "[eTools] New PCA Required: {{partner_name}}",
    "content": """
    Dear Colleague,

    Please note that there is no PCA for Partner {{partner_name}}. There currently is an ongoing Partnership ref. {{reference_number}} with this partner.

    A PCA with {{partner_name}} must signed as soon as possible. Please take action immediately.

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    Please note that there is no PCA for Partner {{partner_name}}. There currently is an ongoing Partnership ref. {{reference_number}} with this partner.<br />

    A PCA with {{partner_name}} must signed as soon as possible. Please take action immediately.<br />

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
