# Generated by Django 3.2.6 on 2022-12-13 12:34

from django.conf import settings
from django.db import migrations, models, connection


def migrate_visit_staff_members_to_users(apps, schema_editor):
    if connection.tenant.schema_name in ["public", "test"]:
        return

    TPMVisit = apps.get_model('tpm', 'TPMVisit')

    for v in TPMVisit.admin_objects.all():
        v.tpm_partner_focal_points.add(*[
            staff_member.user for staff_member in v.old_tpm_partner_focal_points.all().select_related('user')
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('tpmpartners', '0010_alter_tpmpartnerstaffmember_tpm_partner'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0021_migrate_to_realms'),
        ('tpm', '0011_auto_20221213_1229'),
    ]

    operations = [
        migrations.AddField(
            model_name='tpmvisit',
            name='tpm_partner_focal_points',
            field=models.ManyToManyField(blank=True, related_name='tpm_visits', to=settings.AUTH_USER_MODEL, verbose_name='TPM Focal Points'),
        ),
        migrations.RunPython(migrate_visit_staff_members_to_users, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='tpmvisit',
            name='old_tpm_partner_focal_points',
        ),
    ]