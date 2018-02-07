from __future__ import unicode_literals, print_function

from django.db import migrations, models, connection
import django.db.models.deletion
import django.utils.timezone
from django.contrib.gis.geos import GEOSGeometry
import model_utils.fields
import mptt.fields
from django.db.models import Q



class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0006_auto_20171024_1011'),
        ('reports', '0015_auto_20180129_1921'),
        ('partners', '0058_intervention_locations'),
    ]

    operations = [
        migrations.CreateModel(
            name='Disaggregation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False,
                                                                verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False,
                                                                      verbose_name='modified')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('active', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DisaggregationValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False,
                                                                verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False,
                                                                      verbose_name='modified')),
                ('value', models.CharField(max_length=15)),
                ('active', models.BooleanField(default=False)),
                ('disaggregation',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='disaggregation_values',
                                   to='reports.Disaggregation')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterModelOptions(
            name='indicatorblueprint',
            options={'ordering': ['-id']},
        ),
        migrations.RemoveField(
            model_name='appliedindicator',
            name='disaggregation_logic',
        ),
        migrations.RenameField(
            model_name='indicatorblueprint',
            old_name='name',
            new_name='title',
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='title',
            field=models.CharField(max_length=1024, verbose_name='Title'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='cluster_indicator_id',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Cluster Indicator ID'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='cluster_indicator_title',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='Cluster Indicator Title'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='cluster_name',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='Cluster Name'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False,
                                                      verbose_name='created'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='locations',
            field=models.ManyToManyField(related_name='applied_indicators', to='locations.Location',
                                         verbose_name='Location'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False,
                                                           verbose_name='modified'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='response_plan_name',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='Response plan name'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.Sector', verbose_name='Section'),
        ),
        migrations.AddField(
            model_name='indicator',
            name='created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False,
                                                      verbose_name='created'),
        ),
        migrations.AddField(
            model_name='indicator',
            name='modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False,
                                                           verbose_name='modified'),
        ),
        migrations.AddField(
            model_name='indicatorblueprint',
            name='calculation_formula_across_locations',
            field=models.CharField(
                choices=[('sum', 'sum'), ('max', 'max'), ('avg', 'avg'), ('percentage', 'percentage'),
                         ('ratio', 'ratio')], default='sum', max_length=10,
                verbose_name='Calculation Formula across Locations'),
        ),
        migrations.AddField(
            model_name='indicatorblueprint',
            name='calculation_formula_across_periods',
            field=models.CharField(
                choices=[('sum', 'sum'), ('max', 'max'), ('avg', 'avg'), ('percentage', 'percentage'),
                         ('ratio', 'ratio')], default='sum', max_length=10,
                verbose_name='Calculation Formula across Periods'),
        ),
        migrations.AddField(
            model_name='indicatorblueprint',
            name='created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False,
                                                      verbose_name='created'),
        ),
        migrations.AddField(
            model_name='indicatorblueprint',
            name='display_type',
            field=models.CharField(choices=[('number', 'number'), ('percentage', 'percentage'), ('ratio', 'ratio')],
                                   default='number', max_length=10, verbose_name='Display Type'),
        ),
        migrations.AddField(
            model_name='indicatorblueprint',
            name='modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False,
                                                           verbose_name='modified'),
        ),
        migrations.AddField(
            model_name='result',
            name='created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False,
                                                      verbose_name='created'),
        ),
        migrations.AddField(
            model_name='result',
            name='modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False,
                                                           verbose_name='modified'),
        ),
        migrations.AddField(
            model_name='sector',
            name='created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False,
                                                      verbose_name='created'),
        ),
        migrations.AddField(
            model_name='sector',
            name='modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False,
                                                           verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='assumptions',
            field=models.TextField(blank=True, null=True, verbose_name='Assumptions'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='baseline',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Baseline'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='indicator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.IndicatorBlueprint', verbose_name='Indicator'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='lower_result',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applied_indicators',
                                    to='reports.LowerResult', verbose_name='PD Result'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='means_of_verification',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Means of Verification'),
        ),
        migrations.AlterField(
            model_name='appliedindicator',
            name='target',
            field=models.PositiveIntegerField(default=0, verbose_name='Target'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='assumptions',
            field=models.TextField(blank=True, null=True, verbose_name='Assumptions'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='baseline',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Baseline'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='code',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='current',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Current'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='name',
            field=models.CharField(max_length=1024, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='ram_indicator',
            field=models.BooleanField(default=False, verbose_name='RAM Indicator'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='result',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.Result', verbose_name='Result'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='sector',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.Sector', verbose_name='Section'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='sector_current',
            field=models.IntegerField(blank=True, null=True, verbose_name='Sector Current'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='target',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Target'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='unit',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.Unit', verbose_name='Unit'),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='view_on_dashboard',
            field=models.BooleanField(default=False, verbose_name='View on Dashboard'),
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='code',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='description',
            field=models.CharField(blank=True, max_length=3072, null=True, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='disaggregatable',
            field=models.BooleanField(default=False, verbose_name='Disaggregatable'),
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='subdomain',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Subdomain'),
        ),
        migrations.AlterField(
            model_name='indicatorblueprint',
            name='unit',
            field=models.CharField(choices=[('number', 'number'), ('percentage', 'percentage')], default='number',
                                   max_length=10, verbose_name='Unit'),
        ),
        migrations.AlterField(
            model_name='lowerresult',
            name='code',
            field=models.CharField(max_length=50, verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='lowerresult',
            name='name',
            field=models.CharField(max_length=500, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='lowerresult',
            name='result_link',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ll_results',
                                    to='partners.InterventionResultLink'),
        ),
        migrations.AlterField(
            model_name='result',
            name='activity_focus_code',
            field=models.CharField(blank=True, max_length=8, null=True, verbose_name='Activity Focus Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='activity_focus_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Activity Focus Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='code',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='country_programme',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.CountryProgramme', verbose_name='Country Programme'),
        ),
        migrations.AlterField(
            model_name='result',
            name='from_date',
            field=models.DateField(blank=True, null=True, verbose_name='From Date'),
        ),
        migrations.AlterField(
            model_name='result',
            name='gic_code',
            field=models.CharField(blank=True, max_length=8, null=True, verbose_name='GIC Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='gic_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='GIC Name'),
        ),
        migrations.AlterField(
            model_name='result',
            name='hidden',
            field=models.BooleanField(default=False, verbose_name='Hidden'),
        ),
        migrations.AlterField(
            model_name='result',
            name='humanitarian_tag',
            field=models.BooleanField(default=False, verbose_name='Humanitarian Tag'),
        ),
        migrations.AlterField(
            model_name='result',
            name='name',
            field=models.TextField(verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='result',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                             related_name='children', to='reports.Result', verbose_name='Parent'),
        ),
        migrations.AlterField(
            model_name='result',
            name='ram',
            field=models.BooleanField(default=False, verbose_name='RAM'),
        ),
        migrations.AlterField(
            model_name='result',
            name='result_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.ResultType',
                                    verbose_name='Result Type'),
        ),
        migrations.AlterField(
            model_name='result',
            name='sector',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.Sector', verbose_name='Section'),
        ),
        migrations.AlterField(
            model_name='result',
            name='sic_code',
            field=models.CharField(blank=True, max_length=8, null=True, verbose_name='SIC Code'),
        ),
        migrations.AlterField(
            model_name='result',
            name='sic_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='SIC Name'),
        ),
        migrations.AlterField(
            model_name='result',
            name='to_date',
            field=models.DateField(blank=True, null=True, verbose_name='To Date'),
        ),
        migrations.AlterField(
            model_name='result',
            name='vision_id',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='VISION ID'),
        ),
        migrations.AlterField(
            model_name='result',
            name='wbs',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='WBS'),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='disaggregation',
            field=models.ManyToManyField(blank=True, related_name='applied_indicators', to='reports.Disaggregation',
                                         verbose_name='Disaggregation Logic'),
        )
    ]
