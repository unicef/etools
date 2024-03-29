# Generated by Django 3.2.6 on 2022-04-26 11:31

from django.db import migrations


def deactivate_v1_amendments(apps, schema_editor):
    InterventionAmendment = apps.get_model('partners', 'InterventionAmendment')
    for amendment in InterventionAmendment.objects.filter(amended_intervention__isnull=True):
        amendment.signed_by_unicef_date = amendment.signed_date
        amendment.signed_by_partner_date = amendment.signed_date
        amendment.is_active = False
        amendment.save()

        intervention = amendment.intervention
        if intervention.in_amendment:
            intervention.in_amendment = False
            intervention.save()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0098_auto_20220426_1123'),
    ]

    operations = [
        migrations.RunPython(deactivate_v1_amendments, migrations.RunPython.noop),
    ]
