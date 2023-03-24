name = 'partners/partnership/ended/frs/outstanding'
defaults = {
    'description': 'PD Status ended And FR Amount does not equal the Actual Amount.',
    'subject': 'eTools Partnership {{ number }} Fund Reservations',
    'content': """
    Dear Colleague,

    Please note that the Partnership ref. {{ number }} with {{ partner }} has ended but the disbursement
    amount is less than the FR amount.
    Please follow-up with the Partner or adjust your FR.

    {{ url }}.

    Please note that this is an automated message and any response to this email cannot be replied to.
    """,
}
