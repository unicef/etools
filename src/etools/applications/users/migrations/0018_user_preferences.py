# Generated by Django 3.2.6 on 2022-05-30 09:01

from django.db import migrations, models
import etools.applications.users.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_auto_20220408_1558'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='preferences',
            field=models.JSONField(default=etools.applications.users.models.preferences_default_dict),
        ),
    ]
