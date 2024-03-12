from django.conf import settings

from django_tenants.utils import schema_context
from unicef_attachments.models import Attachment

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.last_mile import models
from etools.config.celery import app


@app.task
def notify_upload_waybill(tenant_name, destination_pk, waybill_pk, waybill_url):

    with schema_context(tenant_name):
        destination = models.PointOfInterest.objects.get(pk=destination_pk)
        attachment = Attachment.objects.get(pk=waybill_pk)

        email_context = {
            'user_name': attachment.uploaded_by.full_name,
            'destination': destination.__str__(),
            'waybill_url': waybill_url
        }
        send_notification_with_template(
            recipients=settings.WAYBILL_EMAILS.split(','),
            template_name='last_mile/upload_waybill',
            context=email_context
        )
