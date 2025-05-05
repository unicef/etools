name = 'partners/partnership/created/updated'
defaults = {
    'description': 'The email that is sent when a GPD is added or is updated',
    'subject': 'GPD {{number}} has been {{state}}',
    'content': """
    Dear Colleague,

    GPD {{number}} has been {{state}} here:

    {{url}}

    Thank you.
    """,
    'html_content': """
    Dear Colleague,
    <br/>
    GPD {{number}} has been {{state}} here:
    <br/>
    {{url}}
    <br/>
    Thank you.
    """
}
