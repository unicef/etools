# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_country_vision_last_synced'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0016_auto_20160323_1933'),
        ('partners', '0045_remove_pcafile_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='GovernmentIntervention',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('partner', models.ForeignKey(related_name='work_plans', to='partners.PartnerOrganization')),
                ('result_structure', models.ForeignKey(help_text='Which result structure does this partnership report under?', to='reports.ResultStructure')),
            ],
        ),
        migrations.CreateModel(
            name='GovernmentInterventionResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.CharField(max_length=4)),
                ('planned_amount', models.IntegerField(default=0, verbose_name=b'Planned Cash Transfers')),
                ('activities', models.TextField()),
                ('intervention', models.ForeignKey(related_name='results', to='partners.GovernmentIntervention')),
                ('result', models.ForeignKey(to='reports.Result')),
                ('section', models.ForeignKey(blank=True, to='users.Section', null=True)),
                ('sector', models.ForeignKey(verbose_name=b'Programme/Sector', blank=True, to='reports.Sector', null=True)),
                ('unicef_managers', models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name=b'Unicef focal points', blank=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='recommendation',
            name='assessment',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='amended_at',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='amendment',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='amendment_number',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='cash_for_supply_budget',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='in_kind_amount_budget',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='original',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='partner_contribution_budget',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='partner_mng_email',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='partner_mng_first_name',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='partner_mng_last_name',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='partner_mng_phone',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='total_cash',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='unicef_cash_budget',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='unicef_mng_email',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='unicef_mng_first_name',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='unicef_mng_last_name',
        ),
        migrations.DeleteModel(
            name='Recommendation',
        ),
    ]
