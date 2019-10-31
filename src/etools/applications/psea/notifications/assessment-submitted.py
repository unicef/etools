name = 'psea/assessment/submitted'
defaults = {
    'description': 'Email sent to focal points when PSEA assessment has been submitted by external vendor.',
    'subject': 'PSEA Assessment Submitted: {{ partner.name }}',
    'content': """
    Dear Colleague,

    Please note that a PSEA assessment for the following partner has been submitted:

    Vendor Number: {{ partner.vendor_number }}

    Vendor Name: {{ partner.name }}

    Assessor: {{ assessor }}

    Please click {{ url }} to finalize the report.

    Please note that this is an automated email and the mailbox is not monitored. Please do not reply to it.

    """
}
