from unicef_notification.utils import strip_text

name = 'tpm/visit/assign_staff_member'
defaults = {
    'description': 'Visit assigned. TPM staff member should be notified.',
    'subject': 'Access to eTools Third Party Monitoring Module',

    'content': strip_text("""
    Dear {{ recipient }},

    UNICEF is granting you access to the Third Party Monitoring Module in eTools.
    Please click {{ visit.object_url }} to access your assigned visit.

    Thank you.
    """),

    'html_content': """
    {% extends \"email-templates/base\" %}

    {% block content %}
    Dear {{ recipient }},<br/><br/>

    UNICEF is granting you access to the Third Party Monitoring Module in eTools.<br/>
    Please click <a href=\"{{ visit.object_url }}\">{{ visit.reference_number }}</a>
    to access your assigned visit.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
