name = 'partners/expiring_partner'
defaults = {
    'description': 'Partner Assessment due to expire',
    'subject': 'eTools Partnership {{ partner_name }} Assessment is expiring in {{ days }} days',
    'content': """
    Dear Colleague,

    The assessment for the "HACT" or "Core Value" of Partner {{ partner_name }}
    with Vendor number {{ partner_number }} in {{ country }} is due to expire in {{ days }} days.
    Kindly complete the new assessment and ensure the vendor record is updated with the
    latest risk information promptly to avoid any potential transaction blocks in the system.


    Please note that this is an automated message and any response to this email cannot be replied to.
    """
}
