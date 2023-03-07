name = 'partners/partnership/ending'
defaults = {
    'description': 'PD Ending in 30 or 15 days.',
    'subject': 'eTools Partnership {{ number }} is ending in {{ days }} days',
    'content': """
    Dear Colleague,

    Please note that the Partnership ref {{ number }} with {{ partner }} will end in {{ days }} days.
    Please follow-up with the Partner on status of implementation.

    {{ url }}.

    Please note that this is an automated message and any response to this email cannot be replied to.
    """
}
