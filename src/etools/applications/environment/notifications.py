from unicef_notification.utils import send_notification_with_template as base_send_notification_with_template

from etools.applications.environment.helpers import tenant_switch_is_active


def send_notification_with_template(
    recipients,
    template_name,
    context,
    sender=None,
    from_address='',
    cc=None,
):
    if tenant_switch_is_active('email_disabled') and not tenant_switch_is_active(f'{template_name}_enabled'):
        send_disabled = True
    else:
        send_disabled = False
    base_send_notification_with_template(
        recipients,
        template_name,
        context,
        sender,
        from_address,
        cc,
        send_disabled
    )
