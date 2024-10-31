name = 'last_mile/first_checkin'
defaults = {
    'description': 'First Check-in Triggered',
    'subject': 'Acknowledged by IP',
    'content': """
    Dear Colleague,

    Please note that a new WAYBILL document {{ waybill_url }} was uploaded by {{ user_name }} for destination {{ destination }}.


    Please note that this is an automatically generated message and replies to this email address are not monitored.

    """
}
