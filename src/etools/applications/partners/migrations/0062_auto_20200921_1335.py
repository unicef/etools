# Generated by Django 2.2.7 on 2020-09-21 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0061_merge_20200918_1557'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intervention',
            name='capacity_development',
            field=models.TextField(blank=True, null=True, verbose_name='Capacity Development'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='context',
            field=models.TextField(blank=True, null=True, verbose_name='Context'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='equity_narrative',
            field=models.TextField(blank=True, null=True, verbose_name='Equity Narrative'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='gender_narrative',
            field=models.TextField(blank=True, null=True, verbose_name='Gender Narrative'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='implementation_strategy',
            field=models.TextField(blank=True, null=True, verbose_name='Implementation Strategy'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='ip_program_contribution',
            field=models.TextField(blank=True, null=True, verbose_name='Partner Non-Financial Contribution to Programme'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='other_info',
            field=models.TextField(blank=True, null=True, verbose_name='Other Info'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='other_partners_involved',
            field=models.TextField(blank=True, null=True, verbose_name='Other Partners Involved'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='sustainability_narrative',
            field=models.TextField(blank=True, null=True, verbose_name='Sustainability Narrative'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='technical_guidance',
            field=models.TextField(blank=True, null=True, verbose_name='Technical Guidance'),
        ),
    ]