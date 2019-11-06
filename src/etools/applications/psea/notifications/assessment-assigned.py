name = 'psea/assessment/assigned'
defaults = {
    'description': 'PSEA Assessment Assigned.',
    'subject': 'PSEA Assessment Assigned for {{ partner.name }}',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment was assigned for the following Partner:

    Vendor Number: {{ partner.vendor_number }}

    Vendor Name: {{ partner.name }}

    PSEA Risk Rating: {{ assessment.overall_rating }}

    Date of Assessment: {{ assessment.assessment_date }}

    Please update the Vendor Master Data in VISION accordingly

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """
}
