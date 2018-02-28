from __future__ import absolute_import, division, print_function, unicode_literals

import string
import uuid

from EquiTrack.utils import get_environment
from email_auth.utils import get_token_auth_link
from notification.models import Notification


def generate_username():
    base = 32
    ABC = (string.digits + string.lowercase)[:base]

    uid = uuid.uuid4().int
    digits = []
    while uid:
        digits.append(ABC[uid % base])
        uid //= base

    digits.reverse()
    uid = ''.join(digits)
    return '-'.join([uid[:6], uid[6:10], uid[10:16], uid[16:20], uid[20:]])


def send_invite_email(staff):
    context = {
        'environment': get_environment(),
        'login_link': get_token_auth_link(staff.user)
    }

    notification = Notification.objects.create(
        sender=staff,
        recipients=[staff.user.email], template_name='organisations/staff_member/invite',
        template_data=context
    )
    notification.send_notification()
