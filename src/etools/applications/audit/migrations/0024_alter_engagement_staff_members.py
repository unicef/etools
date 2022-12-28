# Generated by Django 3.2.6 on 2022-11-17 06:43

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('audit', '0023_auto_20220415_1130'),
    ]

    operations = [
        migrations.RenameField(
            model_name='engagement',
            old_name='staff_members',
            new_name='old_staff_members',
        ),
        migrations.RenameField(
            model_name='engagement',
            old_name='authorized_officers',
            new_name='old_authorized_officers',
        ),
    ]
