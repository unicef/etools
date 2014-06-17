__author__ = 'jcranwellward'

from django.conf import settings
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.contrib.sites.models import Site

from registration.signals import user_activated, user_registered

from .tasks import send_mail


@receiver(user_registered)
def send_user_reg_email_to_admins(sender, user, request, **kwargs):
    current_site = Site.objects.get_current()
    send_mail.delay(
        settings.DEFAULT_FROM_EMAIL,
        'registration/profile/created',
        {
            'user_email': user.email,
            'domain': current_site.domain,
            'url': reverse('admin:registration_registrationprofile_changelist')
        },
        'jcranwellward@unicef.org'
    )


@receiver(user_activated)
def send_user_activated_email_to_user(sender, user, request, **kwargs):

    current_site = Site.objects.get_current()
    send_mail.delay(
        settings.DEFAULT_FROM_EMAIL,
        'registration/profile/activated',
        {
            'user_name': user.username,
            'domain': current_site.domain,
        },
        user.email
    )

