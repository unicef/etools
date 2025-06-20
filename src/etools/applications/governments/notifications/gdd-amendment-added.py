name = 'governments/gdd/amendment/added'
defaults = {
    'description': 'The email that is sent when a Government Programme Document amendment is added',
    'subject': '[UNICEF Reporting] New Amendment Added',
    'content': """
    Dear Partner,

    Please note that the UNICEF focal point has initiated an amendment to the Government Programme Document with your organization.
    The details are as follows:

    Government Programme Document Title: {{title}}
    Reference Number: {{reference_number}}
    Amendment Type: {{amendment_type}}

    Depending on the amendment type selected, changes can be made to the strategy, workplan (results structure, budget and supply plan) and GPD timing including reporting and PV requirements of the GPD.

    Please note that this is an automatically generated email and any replies are not monitored.

    """,
    'html_content': """
        Dear Partner,

    Please note that the UNICEF focal point has initiated an amendment to the Government Programme Document with your organization.<br />
    The details are as follows:

    Government Programme Document Title: {{title}}
    Reference Number: {{reference_number}}
    Amendment Type: {{amendment_type}}

    Depending on the amendment type selected, changes can be made to the strategy, workplan (results structure, budget and supply plan) and GPD timing including reporting and PV requirements of the GPD.<br />

    Please note that this is an automatically generated email and any replies are not monitored.

    """
}
