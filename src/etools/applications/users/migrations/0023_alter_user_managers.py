# Generated by Django 3.2.6 on 2023-05-22 11:06

import django.contrib.auth.models
from django.db import migrations
import etools.applications.users.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_userprofile_receive_tpm_notifications'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', etools.applications.users.models.UsersManager()),
                ('base_objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
