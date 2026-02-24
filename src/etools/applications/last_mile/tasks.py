from django.conf import settings
from django.db import connection

from django_tenants.utils import schema_context
from unicef_attachments.models import Attachment
from unicef_notification.utils import send_notification

from etools.applications.environment.models import TenantSwitch
from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.last_mile import models
from etools.applications.last_mile.serializers_ext import TransferIngestAlertSerializer
from etools.applications.users.models import Country, User
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
        recipients = User.objects.get_email_recipients_with_group('Waybill Recipient', tenant_name)

        send_notification_with_template(
            recipients=list(recipients),
            template_name='last_mile/upload_waybill',
            context=email_context
        )


@app.task
def notify_wastage_transfer(tenant_name, transfer, proof_full_url, action='wastage_checkout'):
    action_map = {
        'wastage_checkout': 'checked-out as wastage',
        'short_checkin': 'checked-in as short',
        'surplus_checkin': 'checked-in as surplus'
    }
    with schema_context(tenant_name):
        recipients = User.objects.get_email_recipients_with_group('LMSM Focal Point', tenant_name)
        send_notification(
            recipients=list(recipients),
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject=f"LMSM app: New items {action_map[action]} by {transfer.get('partner_organization', {}).get('name')}",
            html_content_filename='emails/wastage_transfer.html',
            context={'transfer': transfer, 'action': action, 'header': action_map[action], 'proof_full_url': proof_full_url}
        )


@app.task
def notify_dispensing_transfer(tenant_name, transfer, proof_full_url):
    with schema_context(tenant_name):
        recipients = User.objects.get_email_recipients_with_group('LMSM Dispensing Notification', tenant_name)
        send_notification(
            recipients=list(recipients),
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject=f"LMSM app: New items checkout-out as dispensing by {transfer.get('partner_organization', {}).get('name')}",
            html_content_filename='emails/dispense_transfer.html',
            context={'transfer': transfer, 'proof_full_url': proof_full_url}
        )


@app.task
def notify_first_checkin_transfer(tenant_name, transfer_pk, attachment_url):
    with schema_context(tenant_name):
        transfer = models.Transfer.objects.get(pk=transfer_pk)

        recipients = User.objects.get_email_recipients_with_group('LMSM Alert Receipt', tenant_name)

        send_notification(
            recipients=list(recipients),
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject='Acknowledged by IP',
            html_content_filename='emails/first_checkin.html',
            context={'transfer': transfer, "attachment_url": attachment_url}
        )


@app.task
def notify_transfer_ingest_alerts():
    disabled_country_ids = TenantSwitch.objects.filter(
        name='lmsm_disabled', active=True
    ).values_list('countries__id', flat=True)

    for country in Country.objects.exclude(
        schema_name='public'
    ).exclude(id__in=disabled_country_ids).all():
        connection.set_tenant(country)
        _notify_transfer_ingest_alerts(country.name, country.schema_name)


def _notify_transfer_ingest_alerts(country_name, schema_name):
    alerts = models.TransferIngestAlert.objects.filter(notified=False)
    if not alerts.exists():
        return

    recipients = User.objects.get_email_recipients_with_group('LMSM Transfer Alert', schema_name)
    if not recipients:
        return

    alert_list = TransferIngestAlertSerializer(alerts, many=True).data

    send_notification(
        recipients=list(recipients),
        from_address=settings.DEFAULT_FROM_EMAIL,
        subject=f'LMSM: Transfer Ingest Alert — {country_name}',
        html_content_filename='emails/transfer_ingest_alert.html',
        context={'alerts': alert_list, 'country_name': country_name}
    )

    alerts.update(notified=True)
