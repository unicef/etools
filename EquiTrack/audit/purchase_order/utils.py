from EquiTrack.utils import get_environment
from email_auth.utils import get_token_auth_link

from notification.utils import send_notification_using_email_template


# We can put this to models because get_user_model in drfpasswordless.utils raise AppRegistryNotReady exception.
def send_invite_email(staff, engagement):
    context = {
        'environment': get_environment(),
        'staff_member': staff.user.get_full_name(),
        'engagement': engagement.get_mail_context(),
        'login_link': get_token_auth_link(staff.user),
    }

    send_notification_using_email_template(
        sender=staff,
        recipients=[staff.user.email],
        email_template_name='audit/staff_member/invite',
        context=context
    )
