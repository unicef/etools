from django.conf import settings
from django.template.loader import get_template

from etools.applications.notification.models import Notification


def get_template_content(content, filename):
    # If content given, use that; if filename given, fetch the template
    # from that file and return its content; else, return an empty string.
    if content:
        return content
    if filename:
        template = get_template(filename)
        return template.template
    return ''


def send_notification_using_templates(
        recipients,
        sender=None,
        from_address='',
        cc=None,
        context=None,
        subject_template_filename=None,
        subject_template_content=None,
        text_template_filename=None,
        text_template_content=None,
        html_template_filename=None,
        html_template_content=None,
):
    """
    Send a notification, building the content from templates and
    a rendering context.

    Always uses 'Email' type (no other notification type implemented yet).

    * recipients: list of email strings to address the notification to

    * cc: list of email strings to copy the notification to, or None

    * sender: any object. if present, stored as the ``.sender`` in the notification.
      If it's a User object, its ``.email`` is used as the notification
      "From" address.

    * from_address: If `sender` doesn't provide a From address, this can
      provide an email string to use for it. If this is None and the
      sender doesn't provide an address, then settings.DEFAULT_FROM_EMAIL
      is used.

    * context: dictionary used to render the templates, or None.

    Then, for each of subject, plain text message content, and html text message
    content, you can provide either the raw content, or the name of a template file.
    (If you provide both, the content will be used, not the template file).
    """
    if not (sender or from_address):
        from_address = settings.DEFAULT_FROM_EMAIL

    # Let the model handle parameter validation by creating the instance and 'cleaning' it before saving.
    notification = Notification(
        type='Email',
        sender=sender,
        from_address=from_address,
        recipients=recipients,
        cc=cc or [],
        template_data=context,
        subject=get_template_content(subject_template_content, subject_template_filename),
        text_message=get_template_content(text_template_content, text_template_filename),
        html_message=get_template_content(html_template_content, html_template_filename),
    )
    notification.full_clean()
    notification.save()
    notification.send_notification()


def send_notification_using_email_template(
    recipients,
    email_template_name,
    context,
    sender=None,
    from_address='',
    cc=None,
):
    """
    Send an email notification using an EmailTemplate object as the source of
    the templates.

    Always uses 'Email' type (no other notification type implemented yet).

    * recipients: list of email strings to address the notification to

    * cc: list of email strings to copy the notification to, or None

    * sender: any object. if present, stored as the ``.sender`` in the notification.
      If it's a User object, its ``.email`` is used as the notification
      "From" address.

    * from_address: If `sender` doesn't provide a From address, this can
      provide an email string to use for it. If this is None and the
      sender doesn't provide an address, then settings.DEFAULT_FROM_EMAIL
      is used.

    * context: dictionary used to render the templates, or None.

    * email_template_name: name of email template to use (there must be a EmailTemplate
      record with that name)
    """
    if not (sender or from_address):
        from_address = settings.DEFAULT_FROM_EMAIL

    assert email_template_name

    # Let the model handle parameter validation by creating the instance and 'cleaning' it before saving.
    notification = Notification(
        type='Email',
        sender=sender,
        from_address=from_address,
        recipients=recipients,
        cc=cc or [],
        template_name=email_template_name,
        template_data=context,
    )
    notification.full_clean()
    notification.save()
    notification.send_notification()
