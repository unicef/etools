# Generated by Django 2.2.1 on 2019-07-08 16:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('attachments', '0015_auto_20190227_1332'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='filetype',
            unique_together=None,
        ),
        migrations.DeleteModel(
            name='Attachment',
        ),
        migrations.DeleteModel(
            name='FileType',
        ),
    ]
