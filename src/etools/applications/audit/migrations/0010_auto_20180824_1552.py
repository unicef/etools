# Generated by Django 1.10.8 on 2018-08-24 15:52
from __future__ import unicode_literals

from django.db import migrations, models


def migrate_nulls_to_zero(apps, schema_editor):
    Engagement = apps.get_model('audit', 'Engagement')
    Audit = apps.get_model('audit', 'Audit')
    SpotCheck = apps.get_model('audit', 'SpotCheck')

    Audit.objects.filter(audited_expenditure__isnull=True).update(audited_expenditure=0)
    Audit.objects.filter(financial_findings__isnull=True).update(financial_findings=0)
    Engagement.objects.filter(additional_supporting_documentation_provided__isnull=True).update(additional_supporting_documentation_provided=0)
    Engagement.objects.filter(amount_refunded__isnull=True).update(amount_refunded=0)
    Engagement.objects.filter(justification_provided_and_accepted__isnull=True).update(justification_provided_and_accepted=0)
    Engagement.objects.filter(write_off_required__isnull=True).update(write_off_required=0)
    Engagement.objects.filter(exchange_rate__isnull=True).update(exchange_rate=0)
    Engagement.objects.filter(total_value__isnull=True).update(total_value=0)
    SpotCheck.objects.filter(total_amount_of_ineligible_expenditure__isnull=True).update(total_amount_of_ineligible_expenditure=0)
    SpotCheck.objects.filter(total_amount_tested__isnull=True).update(total_amount_tested=0)


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0009_auto_20180521_1052'),
    ]

    operations = [
        migrations.RunPython(migrate_nulls_to_zero, migrations.RunPython.noop),
    ]
