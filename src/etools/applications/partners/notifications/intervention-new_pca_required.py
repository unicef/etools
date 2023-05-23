name = "partners/intervention/new_pca_required"
defaults = {
    "description": "New PCA Required",
    "subject": "[eTools] New PCA Required: {{partner_name}}",
    "content": """
    Dear Colleague,

    Please note that the Partnership ref. {{reference_number}} with {{partner_name}} has an end date that goes beyond the current Country Programme Cycle.

    A new PCA will have to be signed with the partner for the new Country Programme.

    {{pd_link}}

    Please generate a new PCA with {{partner_name}} as soon as possible.

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear Colleague,<br /><br />

    Please note that the Partnership ref. {{reference_number}} with {{partner_name}} has an end date that goes beyond the current Country Programme Cycle.<br />

    A new PCA will have to be signed with the partner for the new Country Programme.</br >

    {{pd_link}}<br />

    Please generate a new PCA with {{partner_name}} as soon as possible.<br/>

    Please note that this is an automated message and replies to this email address are not monitored.<br />
    {% endblock content %}
    """
}
