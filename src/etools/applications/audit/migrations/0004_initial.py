# Generated by Django 3.2.6 on 2022-04-20 16:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('audit', '0003_initial'),
        ('reports', '0001_initial'),
        ('partners', '0001_initial'),
        ('purchase_order', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='engagement',
            name='offices',
            field=models.ManyToManyField(blank=True, related_name='engagements', to='reports.Office', verbose_name='Offices'),
        ),
        migrations.AddField(
            model_name='engagement',
            name='partner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='partners.partnerorganization', verbose_name='Partner'),
        ),
        migrations.AddField(
            model_name='engagement',
            name='po_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='purchase_order.purchaseorderitem', verbose_name='PO Item Number'),
        ),
        migrations.AddField(
            model_name='engagement',
            name='sections',
            field=models.ManyToManyField(blank=True, related_name='engagements', to='reports.Section', verbose_name='Sections'),
        ),
        migrations.AddField(
            model_name='engagement',
            name='staff_members',
            field=models.ManyToManyField(to='purchase_order.AuditorStaffMember', verbose_name='Staff Members'),
        ),
    ]
