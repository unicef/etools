name = 'psea/assessment/assigned'
defaults = {
    'description': 'PSEA Assessment Assigned.',
    'subject': 'PSEA Assessment Assigned',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment has been assigned for the following Partner:

    Vendor Number: {{ assessment.partner.vendor_number }}

    Vendor Name: {{ assessment.partner.name }}

    Date of Assessment: {{ assessment.assessment_date }}

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """
}
