# Generated by Django 1.10.8 on 2018-09-26 13:10
from __future__ import unicode_literals

from django.db import migrations


def update_visit_report_attachment(apps, schema_editor):
    Attachment = apps.get_model('unicef_attachments', 'Attachment')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    tpmvisit_ct = ContentType.objects.get(app_label='tpm', model='tpmvisit')

    Attachment.objects.filter(content_type=tpmvisit_ct).update(code='visit_report_attachments')


class Migration(migrations.Migration):

    dependencies = [
        ('tpm', '0006_auto_20180522_0736'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('unicef_attachments', '0002_attachmentlink'),
    ]

    operations = [
        migrations.RunPython(update_visit_report_attachment, migrations.RunPython.noop),
    ]
