# Generated by Django 2.2.4 on 2019-08-06 14:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0004_auto_20190715_2047'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sectionhistory',
            name='history_type',
            field=models.CharField(choices=[('create', 'Create'), ('merge', 'Merge'), ('close', 'Close')], max_length=10, verbose_name='Name'),
        ),
    ]
