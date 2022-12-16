name = 'partners/partnership/created/updated'
defaults = {
    'description': 'The email that is sent when a PD/SPD is added or is updated',
    'subject': 'PD/SPD {{number}} has been {{state}}',
    'content': """
    Dear Colleague,

    PD/SPD {{number}} has been {{state}} here:

    {{url}}

    Thank you.
    """,
    'html_content': """
    Dear Colleague,
    <br/>
    PD/SPD {{number}} has been {{state}} here:
    <br/>
    {{url}}
    <br/>
    Thank you.
    """
}
