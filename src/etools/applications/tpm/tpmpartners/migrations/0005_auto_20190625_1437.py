# Generated by Django 2.2.2 on 2019-06-25 14:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tpmpartners', '0004_auto_20180503_1311'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tpmpartner',
            options={'ordering': ('name',), 'verbose_name': 'Organization', 'verbose_name_plural': 'Organizations'},
        ),
    ]
