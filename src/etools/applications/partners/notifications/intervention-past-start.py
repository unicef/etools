name = 'partners/intervention/past-start'
defaults = {
    'description': 'Intervention past start date.',
    'subject': 'eTools PD/SPD Past Start Notification',
    'content': """
    Dear Colleague,

    You are the focal point for the Programme Document / SPD {{ reference_number }} {{ title }}.

    Please note that the start date of your document has passed, but as yet no FR information has been entered into eTools.

    Please follow the link below to add the FR information to your document.

    {{ url }}

    Thank you.

    Please note that replies to this email message are not monitored and cannot be replied to.
    """
}
