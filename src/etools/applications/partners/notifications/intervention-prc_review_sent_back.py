name = "partners/intervention/prc_review_sent_back"
defaults = {
    "description": "PD Sent Back by Secretary",
    "subject": "[eTools] PD Sent Back by Secretary",
    "content": """
    Dear Colleague,

    The PRC secretary has sent back the request for PRC Approval on PD {{reference_number}}. Please review and address the comments here: [[PD url to /review - url for unicef (includes pmp)]] {{pd_link}}

    This action cancelled all the previous approvals and returned the PD to the `Development phase. Please complete all the desired/recommended changes. When all changes are completed, the PD will need to be "accepted as final" by both the Partner and UNICEF and resubmitted for "Review".

    Please do not reply to this email.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br />
    The PRC secretary has sent back the request for PRC Approval on PD {{reference_number}}. Please review and address the comments here: [[PD url to /review - url for unicef (includes pmp)]] {{pd_link}}<br />

    This action cancelled all the previous approvals and returned the PD to the `Development phase. Please complete all the desired/recommended changes. When all changes are completed, the PD will need to be "accepted as final" by both the Partner and UNICEF and resubmitted for "Review".<br />

    Please do not reply to this email.<br />
    {% endblock content %}
    """
}
