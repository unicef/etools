# Generated by Django 2.2.7 on 2020-07-20 09:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0046_auto_20200716_1733'),
        ('reports', '0025_auto_20191220_2022'),
    ]

    operations = [
        migrations.AddField(
            model_name='lowerresult',
            name='intervention',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='draft_ll_results', to='partners.Intervention'),
        ),
        migrations.AlterField(
            model_name='lowerresult',
            name='result_link',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ll_results', to='partners.InterventionResultLink', verbose_name='Result Link'),
        ),
    ]
