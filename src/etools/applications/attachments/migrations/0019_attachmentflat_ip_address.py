# Generated by Django 3.2.6 on 2021-11-24 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attachments', '0018_remove_attachmentflat_created'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachmentflat',
            name='ip_address',
            field=models.GenericIPAddressField(default='0.0.0.0'),
        ),
    ]
