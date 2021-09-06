name = 'partners/intervention/prc_review_notification'
defaults = {
    'description': 'Sent manually by PRC secretary from intervention review tab.',
    'subject': 'PD/SSFA {{intervention_number}} Available For Review',
    'content': """
    Dear Colleague,

    Please review Programme Document / SSFA {{ intervention_number }} before {{ meeting_date }}.

    Please follow the link below to check details.

    {{ url }}

    Thank you.

    Please note that replies to this email message are not monitored and cannot be replied to.
    """
}
