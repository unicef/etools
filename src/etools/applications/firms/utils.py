import string
import uuid

from django.urls import reverse

from unicef_notification.utils import send_notification_with_template

from etools.libraries.djangolib.utils import get_environment


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
        'login_link': reverse('social:begin', kwargs={'backend': 'azuread-b2c-oauth2'})
    }

    send_notification_with_template(
        recipients=[staff.user.email],
        template_name='organisations/staff_member/invite',
        context=context
    )
