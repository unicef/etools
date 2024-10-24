name = "governments/gdd/prc_review_sent_back"
defaults = {
    "description": "GDD Sent Back by Secretary",
    "subject": "[eTools] GDD Sent Back by Secretary",
    "content": """
    Dear Colleague,

    The PRC secretary has sent back the request for PRC Approval on GDD {{reference_number}}. Please review and address the comments here: [[GDD url to /review - url for unicef (includes pmp)]] {{gdd_link}}

    This action cancelled all the previous approvals and returned the GDD to the `Development phase. Please complete all the desired/recommended changes. When all changes are completed, the GDD will need to be "accepted as final" by both the Partner and UNICEF and resubmitted for "Review".

    Please do not reply to this email.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br />
    The PRC secretary has sent back the request for PRC Approval on GDD {{reference_number}}. Please review and address the comments here: [[GDD url to /review - url for unicef (includes pmp)]] {{gdd_link}}<br />

    This action cancelled all the previous approvals and returned the GDD to the `Development phase. Please complete all the desired/recommended changes. When all changes are completed, the GDD will need to be "accepted as final" by both the Partner and UNICEF and resubmitted for "Review".<br />

    Please do not reply to this email.<br />
    {% endblock content %}
    """
}
