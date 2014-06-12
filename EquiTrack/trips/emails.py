__author__ = 'jcranwellward'

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.sites.models import Site

from post_office import mail
from celery import shared_task

from .models import Trip


@shared_task
def _send_mail(sender, template, variables, *recipients):
    mail.send(
        [recp for recp in recipients],
        sender,
        template=template,
        context=variables,
    )


@receiver(post_save, sender=Trip)
def send_trip_request(sender, instance, created, **kwargs):
    if created:
        current_site = Site.objects.get_current()
        _send_mail.delay(
            instance.owner.email,
            'trips/trip/created',
            {
                'owner_name': instance.owner.username,
                'supervisor_name': instance.supervisor.username,
                'url': current_site.domain + instance.get_admin_url()
            },
            instance.supervisor.email
        )
