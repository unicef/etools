from django.conf import settings

from django_tenants.utils import schema_context
from unicef_attachments.models import Attachment
from unicef_notification.utils import send_notification

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.last_mile import models
from etools.applications.users.models import User
from etools.config.celery import app


@app.task
def notify_upload_waybill(tenant_name, destination_pk, waybill_pk, waybill_url):

    with schema_context(tenant_name):
        destination = models.PointOfInterest.objects.get(pk=destination_pk)
        attachment = Attachment.objects.get(pk=waybill_pk)

        email_context = {
            'user_name': attachment.uploaded_by.full_name,
            'destination': f'{destination.__str__()} / {tenant_name.capitalize()}',
            'waybill_url': waybill_url
        }
        recipients = User.objects\
            .filter(realms__country__schema_name=tenant_name, realms__group__name='Waybill Recipient')\
            .values_list('email', flat=True)\
            .distinct()

        send_notification_with_template(
            recipients=list(recipients),
            template_name='last_mile/upload_waybill',
            context=email_context
        )


@app.task
def notify_short_transfer(tenant_name, transfer_pk):
    with schema_context(tenant_name):
        email_context = {
            'transfer': models.Transfer.objects.get(pk=transfer_pk)
        }
        # TODO send to Rob for now
        recipients = User.objects.filter(id=1).values_list('email', flat=True)

        send_notification_with_template(
            recipients=list(recipients),
            template_name='last_mile/short_transfer',
            context=email_context
        )


@app.task
def notify_wastage_transfer(tenant_name, transfer_pk):
    with schema_context(tenant_name):
        transfer = models.Transfer.objects.get(pk=transfer_pk)

        # TODO send to Rob for now
        recipients = User.objects.filter(id=1).values_list('email', flat=True)
        send_notification(
            recipients=list(recipients),
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject=f'LMSM app: New items checked out as wastage by {transfer.partner_organization.name}',
            html_content_filename='emails/wastage_transfer.html',
            context={'transfer': transfer}
        )
