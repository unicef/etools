name = 'psea/assessment/rejected'
defaults = {
    'description': 'PSEA Assessment Rejected.',
    'subject': 'PSEA Assessment Rejected',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment has been rejected for the following Partner:

    Vendor Number: {{ assessment.partner.vendor_number }}

    Vendor Name: {{ assessment.partner.name }}

    Date of Assessment: {{ assessment.assessment_date }}

    Comment: {{ assessment.rejected_comment }}

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """
}
