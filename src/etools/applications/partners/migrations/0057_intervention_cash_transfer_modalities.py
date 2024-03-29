# Generated by Django 2.2.7 on 2020-08-27 14:05

import django.contrib.postgres.fields
from django.db import migrations, models
import etools.applications.partners.models


def migrate_cash_transfer_modalities(apps, schema_editor):
    Intervention = apps.get_model('partners', 'Intervention')
    for intervention in Intervention.objects.all():
        intervention.cash_transfer_modalities_new = [intervention.cash_transfer_modalities]
        intervention.save()


def migrate_cash_transfer_modalities_backward(apps, schema_editor):
    Intervention = apps.get_model('partners', 'Intervention')
    for intervention in Intervention.objects.all():
        intervention.cash_transfer_modalities = intervention.cash_transfer_modalities_new[0]
        intervention.save()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0056_auto_20200824_0917'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='cash_transfer_modalities_new',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('payment', 'Direct Payment'), ('reimbursement', 'Reimbursement'), ('dct', 'Direct Cash Transfer')], max_length=50, verbose_name='Cash Transfer Modalities'), default=etools.applications.partners.models.get_default_cash_transfer_modalities, size=None),
        ),
        migrations.RunPython(migrate_cash_transfer_modalities, migrate_cash_transfer_modalities_backward),
    ]
