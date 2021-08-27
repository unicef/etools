name = 'partners/partnership/signed/frs'
defaults = {
    'description': 'Partnership signed with future start date that has no Fund Reservations',
    'subject': 'eTools Intervention {{ number }} does not have any FRs',
    'content': """
    Dear Colleague,

    Please note that the Partnership ref. {{ number }} with {{ partner }} is signed, the start date for the
    PD/SPD is {{ start_date }} and there is no FR associated with this partnership in eTools.
    Please log into eTools and add the FR number to the record, so that the programme document/SSFA status
    can change to active.

    {{ url }}.

    Please note that this is an automated message and any response to this email cannot be replied to.
    """
}
