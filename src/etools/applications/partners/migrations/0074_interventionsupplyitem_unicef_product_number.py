# Generated by Django 2.2.7 on 2020-11-12 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0073_merge_20201112_0759'),
    ]

    operations = [
        migrations.AddField(
            model_name='interventionsupplyitem',
            name='unicef_product_number',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='UNICEF Product Number'),
        ),
    ]