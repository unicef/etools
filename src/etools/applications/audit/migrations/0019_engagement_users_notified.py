# Generated by Django 2.2.6 on 2019-11-06 22:04

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_auto_20190513_1804'),
        ('audit', '0018_auto_20191008_2235'),
    ]

    operations = [
        migrations.AddField(
            model_name='engagement',
            name='users_notified',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='Notified When Completed'),
        ),
    ]
