# Generated by Django 3.2.6 on 2022-11-17 06:43

from django.conf import settings
from django.db import migrations, models, connection


def migrate_engagement_staff_members_to_users(apps, schema_editor):
    if connection.tenant.schema_name in ["public", "test"]:
        return

    Engagement = apps.get_model('audit', 'Engagement')

    for e in Engagement.objects.all():
        e.staff_members.add(*[staff_member.user for staff_member in e.old_staff_members.all().select_related('user') if staff_member.user])


def migrate_engagement_authorized_officers_to_users(apps, schema_editor):
    if connection.tenant.schema_name in ["public", "test"]:
        return

    Engagement = apps.get_model('audit', 'Engagement')

    for e in Engagement.objects.all():
        e.authorized_officers.add(*[staff_member.user for staff_member in e.old_authorized_officers.all().select_related('user') if staff_member.user])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0021_migrate_to_realms'),
        ('purchase_order', '0012_alter_auditorstaffmember_auditor_firm'),
        ('audit', '0024_alter_engagement_staff_members'),
    ]

    operations = [
        migrations.AddField(
            model_name='engagement',
            name='staff_members',
            field=models.ManyToManyField(related_name='engagements', to=settings.AUTH_USER_MODEL, verbose_name='Staff Members'),
        ),
        migrations.AddField(
            model_name='engagement',
            name='authorized_officers',
            field=models.ManyToManyField(related_name='engagement_authorizations', to=settings.AUTH_USER_MODEL, verbose_name='Authorized Officers', blank=True),
        ),
        migrations.RunPython(migrate_engagement_staff_members_to_users, migrations.RunPython.noop),
        migrations.RunPython(migrate_engagement_authorized_officers_to_users, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='engagement',
            name='old_staff_members',
        ),
        migrations.RemoveField(
            model_name='engagement',
            name='old_authorized_officers',
        ),
    ]
