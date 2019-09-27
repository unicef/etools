# Generated by Django 1.9.10 on 2018-02-21 12:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_fix_null_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliedindicator',
            name='assumptions',
            field=models.TextField(blank=True, default='', verbose_name='Assumptions'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='cluster_indicator_title',
            field=models.CharField(blank=True, default='', max_length=1024, verbose_name='Cluster Indicator Title'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='cluster_name',
            field=models.CharField(blank=True, default='', max_length=512, verbose_name='Cluster Name'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='context_code',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Code in current context'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='means_of_verification',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Means of Verification'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='response_plan_name',
            field=models.CharField(blank=True, default='', max_length=1024, verbose_name='Response plan name'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='assumptions',
            field=models.TextField(blank=True, default='', verbose_name='Assumptions'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='baseline',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Baseline'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='code',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='target',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Target'),
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='description',
            field=models.CharField(blank=True, default='', max_length=3072, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='subdomain',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Subdomain'),
        ),
        migrations.AlterField(
            model_name='result',
            name='activity_focus_code',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='Activity Focus Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='activity_focus_name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Activity Focus Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='code',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='gic_code',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='GIC Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='gic_name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='GIC Name'),
        ),
        migrations.AlterField(
            model_name='result',
            name='sic_code',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='SIC Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='sic_name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='SIC Name'),
        ),
        migrations.AlterField(
            model_name='result',
            name='vision_id',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='VISION ID'),
        ),
        migrations.AlterField(
            model_name='section',
            name='alternate_name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Alternate Name'),
        ),
        migrations.AlterField(
            model_name='section',
            name='color',
            field=models.CharField(blank=True, default='', max_length=7, verbose_name='Color'),
        ),
        migrations.AlterField(
            model_name='section',
            name='description',
            field=models.CharField(blank=True, default='', max_length=256, verbose_name='Description'),
        ),
    ]
