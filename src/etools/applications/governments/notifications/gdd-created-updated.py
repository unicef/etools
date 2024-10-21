name = 'partners/partnership/created/updated'
defaults = {
    'description': 'The email that is sent when a GDD is added or is updated',
    'subject': 'GDD {{number}} has been {{state}}',
    'content': """
    Dear Colleague,

    GDD {{number}} has been {{state}} here:

    {{url}}

    Thank you.
    """,
    'html_content': """
    Dear Colleague,
    <br/>
    GDD {{number}} has been {{state}} here:
    <br/>
    {{url}}
    <br/>
    Thank you.
    """
}
