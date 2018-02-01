from django.conf import settings

from notification.models import Notification


def send_notification(
    type,
    recipients,
    sender=None,
    from_address='',
    cc=None,
    template='',
    context=None,
    subject='',
    text_message='',
    html_message='',
):
    """
    Send a notification, building the content from a template and
    a rendering context.

    * type: must be 'Email'
    * recipients: list of email strings to address the notification to
    * cc: list of email strings to copy the notification to, or None
    * template: name of email template to use (there must be a EmailTemplate
      record with that name)
    * context: dictionary used to render the template, or None

    * sender: any object. if present, stored as the ``.sender`` in the notification.
      If it's a User object, its ``.email`` is used as the notification
      "From" address.

    * from_address: If `sender` doesn't provide a From address, this can
      provide an email string to use for it. If this is None and the
      sender doesn't provide an address, then settings.DEFAULT_FROM_EMAIL
      is used.

    * text_message: plain text message to use instead of using template/context
    * html_message: HTML message to use instead of using template/context
    """
    if not (sender or from_address):
        from_address = settings.DEFAULT_FROM_EMAIL

    # Let the model handle parameter validation by creating the instance and 'cleaning' it before saving.
    notification = Notification(
        type=type,
        sender=sender,
        from_address=from_address,
        recipients=recipients,
        cc=cc or [],
        template_name=template,
        template_data=context,
        subject=subject,
        text_message=text_message,
        html_message=html_message,
    )
    notification.full_clean()
    notification.save()
    notification.send_notification()
