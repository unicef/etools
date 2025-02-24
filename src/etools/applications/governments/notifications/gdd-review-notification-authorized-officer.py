name = 'governments/gdd/review_notification_authorized_officer'
defaults = {
    'description': 'Sent manually from intervention review tab.',
    'subject': 'GDD {{ gdd_number }} Available For Review',
    'content': """
    Dear Colleague,

    Please review Government Digital Document {{ gdd_number }}.

    Please follow the link below to access the documents for your review.

    {{ url }}

    Thank you.

    Please note that replies to this email message are not monitored and cannot be replied to.
    """
}
