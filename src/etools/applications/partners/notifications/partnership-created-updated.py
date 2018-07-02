name = 'partners/partnership/created/updated'
defaults = {
    'description': 'The email that is sent when a PD/SSFA is added or is updated',
    'subject': 'PD/SSFA {{number}} has been {{state}}',
    'content': """
    Dear Colleague,

    PD/SSFA {{number}} has been {{state}} here:

    {{url}}

    Thank you.
    """,
    'html_content': """
    Dear Colleague,
    <br/>
    PD/SSFA {{number}} has been {{state}} here:
    <br/>
    {{url}}
    <br/>
    Thank you.
    """
}
