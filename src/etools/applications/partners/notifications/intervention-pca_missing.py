name = "partners/intervention/pca_missing"
defaults = {
    "description": "New PCA Required",
    "subject": "[eTools] New PCA Required: {{partner_name}}",
    "content": """
    Dear Colleague,

    Currently, there is an ongoing Partnership ref. {{reference_number}} with {{partner_name}} with UNICEF. However, there is no PCA for this.

    A PCA is a required for every partnership. Please generate a new PCA with {{partner_name}} as soon as possible.

    {{pd_link}}

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    Currently, there is an ongoing Partnership ref. {{reference_number}} with {{partner_name}} with UNICEF. However, there is no PCA for this.<br />

    A PCA is a required for every partnership. Please generate a new PCA with {{partner_name}} as soon as possible.<br />

    {{pd_link}}<br />

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
