# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-07-20 17:23
from __future__ import unicode_literals

from django.urls import reverse
from django.db import migrations, models


def update_agreement_link(apps, schema_editor):
    AttachmentFlat = apps.get_model("attachments", "attachmentflat")
    Agreement = apps.get_model("partners", "Agreement")
    for flat in AttachmentFlat.objects.filter(agreement_reference_number__isnull=False):
        agreement = Agreement.objects.get(
            reference_number=flat.agreement_reference_number
        )
        flat.agreement_link = reverse(
            "partners_api:agreement-detail",
            args=[agreement.pk]
        )
        flat.save()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0020_auto_20180719_1815'),
        ('attachments', '0008_auto_20180717_1535'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachmentflat',
            name='agreement_link',
            field=models.URLField(blank=True, verbose_name='Agreement Link'),
        ),
        migrations.RunPython(
            update_agreement_link,
            reverse_code=migrations.RunPython.noop,
        )
    ]
