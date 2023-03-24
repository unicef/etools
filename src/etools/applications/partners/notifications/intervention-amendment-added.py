name = 'partners/intervention/amendment/added'
defaults = {
    'description': 'The email that is sent when an intervention amendment is added',
    'subject': '[UNICEF Reporting] New Amendment Added',
    'content': """
    Dear Partner,

    Please note that the UNICEF focal point has initiated an amendment to the Programme Document with your organization.
    The details are as follows:

    Programme Document Title: {{title}}
    Reference Number: {{reference_number}}
    Amendment Type: {{amendment_type}}

    Depending on the amendment type selected, changes can be made to the strategy, workplan (results structure, budget and supply plan) and PD timing including reporting and PV requirements of the PD.

    Please note that this is an automatically generated email and any replies are not monitored.

    """,
    'html_content': """
        Dear Partner,

    Please note that the UNICEF focal point has initiated an amendment to the Programme Document with your organization.<br />
    The details are as follows:

    Programme Document Title: {{title}}
    Reference Number: {{reference_number}}
    Amendment Type: {{amendment_type}}

    Depending on the amendment type selected, changes can be made to the strategy, workplan (results structure, budget and supply plan) and PD timing including reporting and PV requirements of the PD.<br />

    Please note that this is an automatically generated email and any replies are not monitored.

    """
}
