__author__ = 'jcranwellward'

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.sites.models import Site

from emails.tasks import send_mail


@receiver(post_save)
def send_trip_request(sender, instance, created, **kwargs):
    from .models import Trip
    if sender is Trip:
        current_site = Site.objects.get_current()
        if created:
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

        if instance.approved_by_supervisor:
            if instance.travel_assistant and not instance.transport_booked:
                send_mail.delay(
                    instance.owner.email,
                    'travel/trip/travel_or_admin_assistant',
                    {
                        'owner_name': instance.owner.get_full_name(),
                        'travel_assistant': instance.travel_assistant.get_full_name(),
                        'url': 'http://{}{}'.format(
                            current_site.domain,
                            instance.get_admin_url()
                        )
                    },
                    instance.travel_assistant.email,
                )

            if instance.ta_required and instance.programme_assistant and not instance.ta_approved:
                send_mail.delay(
                    instance.owner.email,
                    'trips/trip/TA_request',
                    {
                        'owner_name': instance.owner.get_full_name(),
                        'pa_assistant': instance.programme_assistant.get_full_name(),
                        'url': 'http://{}{}'.format(
                            current_site.domain,
                            instance.get_admin_url()
                        )
                    },
                    instance.programme_assistant.email,
                )
