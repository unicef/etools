name = 'psea/assessment/final'
defaults = {
    'description': 'PSEA Assessment Final.',
    'subject': 'PSEA Assessment',
    'content': """
    Dear Colleagues,

    Please note that a PSEA assessment was completed for the following Partner:

    Vendor Number: {{ assessment.partner.vendor_number }}

    Vendor Name: {{ assessment.partner.name }}

    PSEA Risk Rating: {{ assessment.overall_rating }}

    Date of Assessment: {{ assessment.assessment_date }}

    Please update the Vendor Master Data in VISION accordingly

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """
}
