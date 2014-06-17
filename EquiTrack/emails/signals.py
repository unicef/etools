__author__ = 'jcranwellward'

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
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


@receiver(post_save)
def send_trip_request(sender, instance, created, **kwargs):
    from trips.models import Trip
    if created and sender is Trip:
        current_site = Site.objects.get_current()
        send_mail.delay(
            instance.owner.email,
            'trips/trip/created',
            {
                'owner_name': instance.owner.get_full_name(),
                'supervisor_name': instance.supervisor.get_full_name(),
                'url': 'http://{}{}'.format(
                    current_site.domain,
                    instance.get_admin_url()
                )
            },
            instance.supervisor.email
        )
