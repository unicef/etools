# Generated by Django 2.0.8 on 2019-01-02 19:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('t2f', '0010_auto_20181229_0249'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoice',
            name='currency',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='travel',
        ),
        migrations.RemoveField(
            model_name='invoiceitem',
            name='fund',
        ),
        migrations.RemoveField(
            model_name='invoiceitem',
            name='grant',
        ),
        migrations.RemoveField(
            model_name='invoiceitem',
            name='invoice',
        ),
        migrations.RemoveField(
            model_name='invoiceitem',
            name='wbs',
        ),
        migrations.DeleteModel(
            name='Invoice',
        ),
        migrations.DeleteModel(
            name='InvoiceItem',
        ),
    ]
