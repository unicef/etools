name = 'last_mile/upload_waybill'
defaults = {
    'description': 'New Waybill Uploaded',
    'subject': 'eTools Last Mile: New Waybill document Uploaded',
    'content': """
    Dear Colleague,

    Please note that a new WAYBILL document was uploaded by {{ user_name }} ({{ vendor_number }}).


    Please note that this is an automatically generated message and replies to this email address are not monitored.

    """
}
