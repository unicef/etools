name = 'partners/intervention/amendment/added'
defaults = {
    'description': 'The email that is sent when an itnervention amendment is added',
    'subject': '[UNICEF Reporting] New Amendment Added',
    'content': """
    Dear Partner,

    Please note that UNICEF focal point has added an amendment to the Programme Document with your organization.
    The details are as follows:

    Programme Document Title: {{title}}
    Reference Number: {{reference_number}}
    Amendment Type: {{amendment_type}}

    Some of these changes, like addition of new indicators or locations, may require that you refresh your reports
    in the Partner Reporting Portal.
    To do so, please hit the "Refresh" button on the report you wish to refresh and the changes will take effect.
    Please note that there hitting refresh will delete data on all of other reports that were not submitted,
     so please make sure that there all drafts are saved before hitting "Refresh".

    Please note that this is an automatically generated email and any replies are not monitored.

    """,
    'html_content': """
        Dear Partner,

    Please note that UNICEF focal point has added an amendment to the Programme Document with your organization.
    The details are as follows:

    Programme Document Title: {{title}}
    Reference Number: {{reference_number}}
    Amendment Type: {{amendment_type}}

    Some of these changes, like addition of new indicators or locations, may require that you refresh your reports
    in the Partner Reporting Portal.
    To do so, please hit the "Refresh" button on the report you wish to refresh and the changes will take effect.
    Please note that there hitting refresh will delete data on all of other reports that were not submitted,
     so please make sure that there all drafts are saved before hitting "Refresh".

    Please note that this is an automatically generated email and any replies are not monitored.

    """
}
