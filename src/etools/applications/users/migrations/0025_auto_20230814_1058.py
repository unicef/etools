# Generated by Django 3.2.19 on 2023-08-14 10:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_stageduser'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='old_groups',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='old_countries_available',
        ),
    ]
