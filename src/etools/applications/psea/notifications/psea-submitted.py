from unicef_notification.utils import strip_text

# Receiver: Vendor Master Team, GSSC
# Subject:

name = 'audit/psea/submitted'
defaults = {
    'description': 'Email sent to focal points when PSEA assessment has been submitted by external vendor.',
    'subject': 'PSEA Assessment',

    'content': strip_text("""
    Dear {{ staff_member }},

    UNICEF is granting you access to the Financial Assurance Module in eTools.
    Please refer below for additional information.

    Engagement Type: {{ engagement.engagement_type }}
    Partner: {{ engagement.partner }}

    Please click this link to complete the report: {{ engagement.object_url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ staff_member }},<br/><br/>

    UNICEF is granting you access to the Financial Assurance Module in eTools.<br/>
    Please refer below for additional information.<br/><br/>

    Engagement Type: {{ engagement.engagement_type }}<br/>
    Partner: {{ engagement.partner }}<br/><br/>

    Please click <a href="{{ engagement.object_url }}">this link</a> to complete the report.<br/><br/>

    Thank you.
    {% endblock %}
    """
}

# Text:
#
# Dear Colleagues,
#
# Please note that a PSEA assessment was completed for the following Partner:
#
# Vendor Number: [Vendor Number]
#
# Vendor Name: [Partner Name]
#
# PSEA Risk Rating: [PSEA Risk Rating]
#
# Date of Assessment: [The date on which the PSEA Assessment was submitted by the Auditor]
#
# Please update the Vendor Master Data in VISION accordingly
#
# Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.
#
