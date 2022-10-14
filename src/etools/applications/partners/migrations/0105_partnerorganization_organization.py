# Generated by Django 3.2.6 on 2022-07-13 12:55
import logging

from django.db import migrations, models, transaction
import django.db.models.deletion


def migrate_organizations(apps, schema_editor):
    Organization = apps.get_model('organizations', 'Organization')
    PartnerOrganization = apps.get_model('partners', 'PartnerOrganization')

    with transaction.atomic():
        for partner_org in PartnerOrganization.objects.all():
            # this should not be the case as Partners should all be sanitized
            if not partner_org.vendor_number:
                logging.info(f"No vendor_number set for Partner "
                             f"{partner_org.name} id: {partner_org.pk}. Skipping..")
                continue
            # update if it already exists as the organization might have been created from
            # AuditorFirms/TPMPartners which don't have an organization_type, cso_type or short_name
            organization, created = Organization.objects.update_or_create(
                vendor_number=partner_org.vendor_number,
                defaults={
                    'name': partner_org.name,
                    'organization_type': partner_org.partner_type,
                    'cso_type': partner_org.cso_type,
                    'short_name': partner_org.short_name,
                })
            if not created:
                logging.info(f'Organization {organization.name} with '
                             f'vendor_number {organization.vendor_number} was updated.')
            partner_org.organization = organization
            partner_org.save(update_fields=['organization'])


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('partners', '0104_auto_20220808_0931'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='partnerorganization',
            options={'base_manager_name': 'objects'},
        ),
        migrations.AlterUniqueTogether(
            name='partnerorganization',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='partnerorganization',
            name='organization',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='partner', to='organizations.organization'),
        ),
        migrations.RunPython(migrate_organizations, migrations.RunPython.noop),
    ]
