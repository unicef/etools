# Generated by Django 3.2.19 on 2024-06-17 09:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('last_mile', '0003_alter_pointofinterest_p_code'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='item',
            options={'base_manager_name': 'objects', 'ordering': ('expiry_date',)},
        ),
    ]
