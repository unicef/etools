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
def notify_wastage_transfer(tenant_name, transfer_pk, action='wastage_checkout'):
    action_map = {
        'wastage_checkout': 'checked-out as wastage',
        'short_checkin': 'checked-in as short',
        'surplus_checkin': 'checked-in as surplus'
    }
    with schema_context(tenant_name):
        transfer = models.Transfer.objects.get(pk=transfer_pk)

        recipients = User.objects \
            .filter(realms__country__schema_name=tenant_name,
                    realms__is_active=True,
                    realms__group__name='LMSM Focal Point') \
            .values_list('email', flat=True) \
            .distinct()
        send_notification(
            recipients=list(recipients),
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject=f'LMSM app: New items {action_map[action]} by {transfer.partner_organization.name}',
            html_content_filename='emails/wastage_transfer.html',
            context={'transfer': transfer, 'action': action, 'header': action_map[action]}
        )


@app.task
def notify_first_checkin_transfer(tenant_name):
    with schema_context(tenant_name):
        recipients = User.objects \
            .filter(realms__country__schema_name=tenant_name,
                    realms__is_active=True,
                    realms__group__name='LMSM Alert Receipt') \
            .values_list('email', flat=True) \
            .distinct()
        email_context = {
            'user_name': 'attachment.uploaded_by.full_name',
            'destination': '{destination.__str__()} / {tenant_name.capitalize()}',
            'waybill_url': 'waybill_url'
        }
        send_notification_with_template(
            recipients=list(recipients),
            template_name='last_mile/first_checkin',
            context=email_context
        )

