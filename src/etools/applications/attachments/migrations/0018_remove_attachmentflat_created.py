# Generated by Django 2.2.7 on 2019-12-13 17:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('attachments', '0017_attachmentflat_created_timestamp'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attachmentflat',
            name='created',
        ),
        migrations.RenameField(
            model_name='attachmentflat',
            old_name='created_timestamp',
            new_name='created',
        ),
    ]
