# Generated by Django 3.2.19 on 2023-08-14 10:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0120_merge_20230502_1523'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agreement',
            name='old_authorized_officers',
        ),
        migrations.RemoveField(
            model_name='agreement',
            name='old_partner_manager',
        ),
        migrations.RemoveField(
            model_name='intervention',
            name='old_partner_authorized_officer_signatory',
        ),
        migrations.RemoveField(
            model_name='intervention',
            name='old_partner_focal_points',
        ),
        migrations.RemoveField(
            model_name='interventionamendment',
            name='old_partner_authorized_officer_signatory',
        ),
        migrations.DeleteModel(
            name='PartnerStaffMember',
        ),
    ]
