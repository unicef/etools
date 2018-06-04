
import string
import uuid

from etools.applications.email_auth.utils import get_token_auth_link
from etools.applications.EquiTrack.utils import get_environment
from etools.applications.notification.utils import send_notification_using_email_template


def generate_username():
    base = 32
    abc_function = (string.digits + string.ascii_lowercase)[:base]

    uid = uuid.uuid4().int
    digits = []
    while uid:
        digits.append(abc_function[uid % base])
        uid //= base

    digits.reverse()
    uid = ''.join(digits)
    return '-'.join([uid[:6], uid[6:10], uid[10:16], uid[16:20], uid[20:]])


def send_invite_email(staff):
    context = {
        'environment': get_environment(),
        'login_link': get_token_auth_link(staff.user)
    }

    send_notification_using_email_template(
        recipients=[staff.user.email],
        email_template_name='organisations/staff_member/invite',
        context=context
    )
