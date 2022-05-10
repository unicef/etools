name = "partners/intervention/prc_review_sent_back"
defaults = {
    "description": "PD Sent Back by Secretary",
    "subject": "[eTools] PD Sent Back by Secretary",
    "content": """
    Dear Colleague,
    The PRC secretary has sent back the request for PRC Approval on PD {{reference_number}}. Please review the comments here: [[PD url to /review - url for unicef (includes pmp)]] {{pd_link}}

    Please do not reply to this email.
    """,
    "html_content": """
    {% extends "email-templates/base" %}
    {% block content %}
    Dear Colleague,<br />
    The PRC secretary has sent back the request for PRC Approval on PD {{reference_number}}. Please review the comments here: [[PD url to /review - url for unicef (includes pmp)]]  {{pd_link}}<br /><br />

    Please do not reply to this email.<br />
    {% endblock content %}
    """
}
