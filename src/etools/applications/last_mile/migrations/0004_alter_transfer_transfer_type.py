# Generated by Django 4.2.3 on 2024-10-25 07:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('last_mile', '0003_alter_item_wastage_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='transfer_type',
            field=models.CharField(blank=True, choices=[('DELIVERY', 'Delivery'), ('DISTRIBUTION', 'Distribution'), ('HANDOVER', 'Handover'), ('WASTAGE', 'Wastage'), ('DISPENSE', 'Dispense')], max_length=30, null=True),
        ),
    ]