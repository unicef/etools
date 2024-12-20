name = 'governments/gdd/past-start'
defaults = {
    'description': 'Intervention past start date.',
    'subject': 'eTools GDD Past Start Notification',
    'content': """
    Dear Colleague,

    Please note that the Partnership ref. {{ reference_number }} {{ title }} with {{ partner_name }} is approved, the start date for the GDD is {{ start_date }}. However, there is no FR associated with this partnership in eTools.
    Please log into eTools and add the FR number to the record, so that the Government Digital Document/GDD status can progress to active status.

    Please follow the link below to add the FR information to your document.

    {{ url }}

    Please note that this is an automated message and any response to this email cannot be replied to.
    """
}
