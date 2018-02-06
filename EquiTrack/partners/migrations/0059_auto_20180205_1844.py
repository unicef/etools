# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-02-05 18:44
from __future__ import unicode_literals

from django.db import migrations


def copy_attached_agreement(apps, schema_editor):
    # Copy attached_agreement field content to
    # attachments model
    FileType = apps.get_model("attachments", "filetype")
    Attachment = apps.get_model("attachments", "attachment")
    Agreement = apps.get_model("partners", "agreement")
    file_type, _ = FileType.objects.get_or_create(
        code="partners_agreement",
        defaults={
            "name": "Attached Agreement",
            "label": "attached_agreement"
        }
    )

    for agreement in Agreement.objects.filter(
            attached_agreement__isnull=False
    ).all():
        Attachment.objects.create(
            content_object=agreement,
            file=agreement.attached_agreement,
            file_type=file_type,
            code=file_type.code,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0058_intervention_locations'),
    ]

    operations = [
        migrations.RunPython(
            copy_attached_agreement,
            reverse_code=migrations.RunPython.noop
        )
    ]
