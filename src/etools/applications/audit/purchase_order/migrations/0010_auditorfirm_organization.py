# Generated by Django 3.2.6 on 2022-08-09 17:16
import logging

from django.db import migrations, models, transaction
import django.db.models.deletion


def migrate_auditor_firms_to_organizations(apps, schema_editor):
    Organization = apps.get_model('organizations', 'Organization')
    AuditorFirm = apps.get_model('purchase_order', 'AuditorFirm')

    with transaction.atomic():
        for auditor_firm in AuditorFirm.objects.all():
            if not auditor_firm.vendor_number:
                logging.info(f"No vendor_number set for AuditorFirm "
                             f"{auditor_firm.name} id: {auditor_firm.pk}")
                continue
            organization, created = Organization.objects.get_or_create(
                vendor_number=auditor_firm.vendor_number,
                defaults={
                    'name': auditor_firm.name,
                    'organization_type': "Auditor Firm"
                })
            # set the organization_type to None if the organization already exists as TPM Partner type
            if not created and organization.organization_type == 'TPM Partner':
                organization.organization_type = None
                organization.save(update_fields=['organization_type'])
            auditor_firm.organization = organization
            auditor_firm.save(update_fields=['organization'])


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('purchase_order', '0009_auto_20210421_1745'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditorfirm',
            name='organization',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='organizations.organization'),
        ),
        migrations.AlterModelOptions(
            name='auditorfirm',
            options={'base_manager_name': 'objects', 'ordering': ('organization__name',), 'verbose_name': 'Organization', 'verbose_name_plural': 'Organizations'},
        ),
        migrations.RunPython(migrate_auditor_firms_to_organizations, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='auditorfirm',
            name='name',
        ),
        migrations.RemoveField(
            model_name='auditorfirm',
            name='vendor_number',
        ),
    ]
