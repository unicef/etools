name = 'psea/assessment/assigned'
defaults = {
    'description': 'PSEA Assessment Assigned.',
    'subject': 'PSEA Assessment Assigned for {{ partner.name }}',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment has been assigned for the following Partner:

    Vendor Number: {{ partner.vendor_number }}

    Vendor Name: {{ partner.name }}

    Please click <a href="{{ url }}">this link</a> to complete the report.<br/><br/>

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """
}
