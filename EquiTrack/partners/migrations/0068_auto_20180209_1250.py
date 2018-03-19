# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-02-09 12:50
from __future__ import unicode_literals

from django.db import migrations


def copy_core_values_assessment(apps, schema_editor):
    # Copy core_values_assessment field content to
    # attachments model
    FileType = apps.get_model("attachments", "filetype")
    Attachment = apps.get_model("attachments", "attachment")
    PartnerOrganization = apps.get_model("partners", "partnerorganization")
    ContentType = apps.get_model("contenttypes", "ContentType")

    file_type, _ = FileType.objects.get_or_create(
        code="partners_partner_assessment",
        defaults={
            "label": "Core Values Assessment",
            "name": "core_values_assessment",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(PartnerOrganization)

    for partner in PartnerOrganization.objects.filter(
        core_values_assessment__isnull=False
    ).all():
        Attachment.objects.create(
            content_type=content_type,
            object_id=partner.pk,
            file=partner.core_values_assessment,
            file_type=file_type,
            code=file_type.code,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0067_auto_20180205_1844'),
        ('attachments', '0005_auto_20180206_1700'),
    ]

    operations = [
        migrations.RunPython(
            copy_core_values_assessment,
            reverse_code=migrations.RunPython.noop
        )
    ]
