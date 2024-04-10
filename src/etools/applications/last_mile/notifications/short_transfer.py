name = 'last_mile/short_transfer'
defaults = {
    'description': 'New Short Transfer Recorded',
    'subject': 'eTools Last Mile: New Loss Transfer Recorded',
    'content': """
    Dear Colleague,

    Please note that a new short transfer was recorded id {{ transfer.pk }}.
    Details:
        Origin: {{ transfer.origin_point.name }}
        Destination: {{ transfer.destination_point.name }}


    Please note that this is an automatically generated message and replies to this email address are not monitored.

    """
}
