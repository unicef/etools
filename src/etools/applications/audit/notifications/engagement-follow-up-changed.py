from unicef_notification.utils import strip_text

name = 'audit/engagement/follow-up-changed'
defaults = {
    'description': 'Email sent when the amounts in the follow-up are changed',
    'subject': 'Verification of Change in Financial Findings Record',

    'content': strip_text("""
    Dear {{ full_name }},

    This is to inform you that changes have been made in the Financial Findings section of the Engagement {{ object_url }} {{ reference_number }}.

    The updated Figures now is:

    Financial Findings: {{ financial_findings }} USD
    Refunded Amount: {{ amount_refunded }} USD
    Additional Supporting Documentation Provided: {{ additional_supporting_documentation_provided }} USD
    Justification Provided and Accepted: {{ justification_provided_and_accepted }} USD
    Pending Unsupported Amount: {{ write_off_required }} USD

    Kindly review and verify these updates at your earliest convenience to ensure accuracy and alignment with our records.

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ full_name }},<br/><br/>

    This is to inform you that changes have been made in the Financial Findings section of the Engagement <a href="{{ object_url }}">{{ reference_number }}</a>. <br/><br/>

    The updated Figures now is: <br/><br/>
    {% if engagement_type == 'audit' %}Financial Findings: {{ financial_findings }} USD <br/>{% endif %}
    Refunded Amount: {{ amount_refunded }} USD <br/>
    Additional Supporting Documentation Provided: {{ additional_supporting_documentation_provided }} USD <br/>
    Justification Provided and Accepted: {{ justification_provided_and_accepted }} USD <br/>
    Pending Unsupported Amount: {{ write_off_required }} USD <br/><br/>

    Kindly review and verify these updates at your earliest convenience to ensure accuracy and alignment with our records.<br/><br/>

    Thank you.

    {% endblock %}
    """
}
