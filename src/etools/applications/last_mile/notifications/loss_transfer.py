name = 'last_mile/loss_transfer'
defaults = {
    'description': 'New Loss Transfer Recorded',
    'subject': 'eTools Last Mile: New Loss Transfer Recorded',
    'content': """
    Dear Colleague,

    Please note that a new loss transfer was recorded id {{ transfer.pk }}.
    Details:
        Origin: {{ transfer.origin_point.name }}
        Destination: {{ transfer.destination_point.name }}


    Please note that this is an automatically generated message and replies to this email address are not monitored.

    """
}
