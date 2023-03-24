name = 'partners/intervention/past-start'
defaults = {
    'description': 'Intervention past start date.',
    'subject': 'eTools PD/SPD Past Start Notification',
    'content': """
    Dear Colleague,

    Please note that the Partnership ref. {{ reference_number }} {{ title }} with {{ partner_name }} is signed, the start date for the PD/SPD is {{ start_date }}. However, there is no FR associated with this partnership in eTools.
    Please log into eTools and add the FR number to the record, so that the programme document/SPD status can progress to active status.

    Please follow the link below to add the FR information to your document.

    {{ url }}

    Please note that this is an automated message and any response to this email cannot be replied to.
    """
}
