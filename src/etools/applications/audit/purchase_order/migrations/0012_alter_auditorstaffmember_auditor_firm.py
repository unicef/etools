# Generated by Django 3.2.6 on 2022-11-17 06:43

from django.db import migrations, models, connection, IntegrityError
import django.db.models.deletion


def migrate_audit_staff_members_to_realms(apps, schema_editor):
    if connection.tenant.schema_name in ["public", "test"]:
        return

    Realm = apps.get_model('users', 'Realm')
    Group = apps.get_model('auth', 'Group')
    AuditorFirm = apps.get_model('purchase_order', 'AuditorFirm')
    Country = apps.get_model("users", "country")
    country = Country.objects.get(schema_name=connection.tenant.schema_name)

    auditor_group = Group.objects.get_or_create(name='Auditor')[0]

    for firm in AuditorFirm.objects.all():
        for staff_member in firm.staff_members.all():
            try:
                Realm.objects.create(
                    user=staff_member.user,
                    country=country,
                    organization=firm.organization,
                    group=auditor_group,
                )
            except IntegrityError:
                # all good, realm already exists
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('purchase_order', '0011_alter_auditorfirm_organization'),
        ('users', '0021_migrate_to_realms'),
        ('auth', '0008_alter_user_username_max_length'),
    ]

    operations = [
        migrations.RunPython(migrate_audit_staff_members_to_realms, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='auditorstaffmember',
            name='auditor_firm',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='old_staff_members', to='purchase_order.auditorfirm', verbose_name='Auditor'),
        ),
    ]
