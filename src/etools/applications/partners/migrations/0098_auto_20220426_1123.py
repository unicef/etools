# Generated by Django 3.2.6 on 2022-04-26 11:23

from django.db import migrations
from django.db.models import Q


def migrate_cash_transfer_choices(apps, schema_editor):
    Intervention = apps.get_model('partners', 'Intervention')
    interventions_to_migrate = Intervention.objects.filter(
        Q(cash_transfer_modalities__contains=['reimburse']) |
        Q(cash_transfer_modalities__contains=['direct'])
    )
    choices_mapping = {
        'reimburse': 'reimbursement',
        'direct': 'dct',
    }
    for intervention in interventions_to_migrate:
        intervention.cash_transfer_modalities = [choices_mapping.get(ct, ct) for ct in intervention.cash_transfer_modalities]
        intervention.save()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0097_intervention_confidential'),
    ]

    operations = [
        migrations.RunPython(migrate_cash_transfer_choices, migrations.RunPython.noop),
    ]