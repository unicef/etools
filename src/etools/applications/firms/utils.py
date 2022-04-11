from django.urls import reverse

from etools.applications.environment.notifications import send_notification_with_template
from etools.libraries.djangolib.utils import get_environment


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
