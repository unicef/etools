# Generated by Django 3.2.6 on 2022-12-13 12:29

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tpmpartners', '0010_alter_tpmpartnerstaffmember_tpm_partner'),
        ('tpm', '0010_auto_20191029_1826'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tpmvisit',
            old_name='tpm_partner_focal_points',
            new_name='old_tpm_partner_focal_points',
        ),
    ]
