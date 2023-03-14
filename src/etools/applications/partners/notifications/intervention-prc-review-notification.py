name = 'partners/intervention/prc_review_notification'
defaults = {
    'description': 'Sent manually by PRC secretary from intervention review tab.',
    'subject': 'PD/SSFA {{intervention_number}} Available For Review',
    'content': """
    Dear Colleague,

    Please review Programme Document / Simplified Programme Document {{ intervention_number }} before {{ meeting_date }}.

    Please follow the link below to access the documents for your review.

    {{ url }}

    Thank you.

    Please note that replies to this email message are not monitored and cannot be replied to.
    """
}
