name = "governments/gdd/unicef_rejected_reviewed"
defaults = {
    "description": "GDD has been reviewed and Rejected",
    "subject": "[eTools] GDD has been reviewed and Rejected",
    "content": """
    Dear Colleague,

    GDD {{reference_number}} has been reviewed and rejected.

    The following comments were provided:
    {{review_comments}}

    The following were listed as suggested actions:
    {{review_actions}}

    {{gdd_link}}

    Please review and address the comments and action points. The GDD will need to be "accepted as final" in order to progress for internal review.

    Please note that this is an automated message and replies to this email address are not monitored.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague, <br /> <br />

    GDD {{reference_number}} has been reviewed and rejected.
    <br />
    <br />
    The following were listed as suggested actions:<br />
    {{review_actions}}
    <br /><br />

    You can review the GDD at the following link:<br />
    {{gdd_link}}<br />

    Please review and address the comments and action points. The GDD will need to be "accepted as final" in order to progress for internal review.<br />

    Please note that this is an automated message and replies to this email address are not monitored.

    {% endblock content %}
    """
}
