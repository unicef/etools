name = 'psea/assessment/rejected'
defaults = {
    'description': 'PSEA Assessment Rejected.',
    'subject': 'PSEA Assessment Rejected for {{ partner_name }}',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment has been rejected for the following Partner:

    Vendor Number: {{ partner_vendor_number }}

    Vendor Name: {{ partner_name }}

    Date of Assessment: {{ assessment_date }}

    Comment: {{ rejected_comment }}

    Please click <a href="{{ url }}">this link</a> to complete the report.<br/><br/>

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """
}
