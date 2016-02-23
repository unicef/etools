# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import smart_selects.db_fields
import filer.fields.file
import EquiTrack.mixins
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('funds', '0001_initial'),
        ('filer', '0002_auto_20150606_2003'),
        ('supplies', '0001_initial'),
        ('reports', '0001_initial'),
        ('locations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Agreement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('start', models.DateTimeField(null=True, verbose_name='start', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='end', blank=True)),
                ('agreement_type', models.CharField(max_length=10, choices=[('PCA', 'Partner Cooperation Agreement'), ('SSFA', 'Small Scale Funding Agreement'), ('MOU', 'Memorandum of Understanding'), ('ic', 'Institutional Contract'), ('AWP', 'Annual Work Plan')])),
                ('agreement_number', models.CharField(help_text='PCA Reference Number', unique=True, max_length=45L)),
                ('attached_agreement', models.FileField(upload_to='agreements', blank=True)),
                ('signed_by_unicef_date', models.DateField(null=True, blank=True)),
                ('signed_by_partner_date', models.DateField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AmendmentLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('type', models.CharField(max_length=50, choices=[(b'No Cost', b'No Cost'), (b'Cost', b'Cost'), (b'Activity', b'Activity'), (b'Other', b'Other')])),
                ('amended_at', models.DateField(null=True)),
                ('amendment_number', models.IntegerField(default=0)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Assessment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=50, choices=[('Micro Assessment', 'Micro Assessment'), ('Simplified Checklist', 'Simplified Checklist'), ('Scheduled Audit report', 'Scheduled Audit report'), ('Special Audit report', 'Special Audit report'), ('Other', 'Other')])),
                ('names_of_other_agencies', models.CharField(help_text='List the names of the other agencies they have worked with', max_length=255, null=True, blank=True)),
                ('expected_budget', models.IntegerField(verbose_name='Planned amount')),
                ('notes', models.CharField(help_text='Note any special requests to be considered during the assessment', max_length=255, null=True, verbose_name='Special requests', blank=True)),
                ('requested_date', models.DateField(auto_now_add=True)),
                ('planned_date', models.DateField(null=True, blank=True)),
                ('completed_date', models.DateField(null=True, blank=True)),
                ('rating', models.CharField(default='high', max_length=50, choices=[('high', 'High'), ('significant', 'Significant'), ('moderate', 'Moderate'), ('low', 'Low')])),
                ('report', models.FileField(null=True, upload_to=b'assessments', blank=True)),
                ('current', models.BooleanField(default=True, verbose_name='Basis for risk rating')),
                ('approving_officer', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AuthorizedOfficer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('agreement', models.ForeignKey(related_name='authorized_officers', to='partners.Agreement')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DistributionPlan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('quantity', models.PositiveIntegerField(help_text='Quantity required for this location')),
                ('send', models.BooleanField(default=False, verbose_name='Send to partner?')),
                ('sent', models.BooleanField(default=False)),
                ('delivered', models.IntegerField(default=0)),
                ('item', models.ForeignKey(to='supplies.SupplyItem')),
                ('location', models.ForeignKey(to='locations.Region')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64L)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GwPCALocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tpm_visit', models.BooleanField(default=False)),
                ('governorate', models.ForeignKey(to='locations.Governorate')),
                ('locality', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'region', chained_field=b'region', blank=True, auto_choose=True, to='locations.Locality', null=True)),
                ('location', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'locality', chained_field=b'locality', blank=True, auto_choose=True, to='locations.Location', null=True)),
            ],
            options={
                'verbose_name': 'Partnership Location',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IndicatorProgress',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('programmed', models.PositiveIntegerField()),
                ('current', models.IntegerField(default=0, null=True, blank=True)),
                ('indicator', models.ForeignKey(to='reports.Indicator')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PartnerOrganization',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(default='national', max_length=50, verbose_name='CSO Type', choices=[('international', 'International'), ('national', 'CSO'), ('cbo', 'CBO'), (('academic',), 'Academic Inst.'), (('foundation',), 'Foundation')])),
                ('partner_type', models.CharField(blank=True, max_length=50, null=True, choices=[('Government', 'Government'), ('Civil Society Organisation', 'Civil Society Organisation'), ('UN Agency', 'UN Agency'), ('Inter-governmental Organisation', 'Inter-governmental Organisation'), ('Bi-Lateral Organisation', 'Bi-Lateral Organisation')])),
                ('name', models.CharField(help_text='Please make sure this matches the name you enter in VISION', unique=True, max_length=255, verbose_name=b'Full Name')),
                ('short_name', models.CharField(max_length=50, blank=True)),
                ('description', models.CharField(max_length=256L, blank=True)),
                ('address', models.TextField(null=True, blank=True)),
                ('email', models.CharField(max_length=255, blank=True)),
                ('phone_number', models.CharField(max_length=32L, blank=True)),
                ('vendor_number', models.BigIntegerField(null=True, blank=True)),
                ('alternate_id', models.IntegerField(null=True, blank=True)),
                ('alternate_name', models.CharField(max_length=255, null=True, blank=True)),
                ('rating', models.CharField(default='high', max_length=50, verbose_name='Risk Rating', choices=[('high', 'High'), ('significant', 'Significant'), ('moderate', 'Moderate'), ('low', 'Low')])),
                ('core_values_assessment_date', models.DateField(null=True, verbose_name='Date positively assessed against core values', blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PartnershipBudget',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('partner_contribution', models.IntegerField(default=0)),
                ('unicef_cash', models.IntegerField(default=0)),
                ('in_kind_amount', models.IntegerField(default=0)),
                ('total', models.IntegerField(default=0)),
                ('amendment', models.ForeignKey(related_name='budgets', blank=True, to='partners.AmendmentLog', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PartnerStaffMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=64L)),
                ('first_name', models.CharField(max_length=64L)),
                ('last_name', models.CharField(max_length=64L)),
                ('email', models.CharField(max_length=128L)),
                ('phone', models.CharField(max_length=64L, blank=True)),
                ('partner', models.ForeignKey(to='partners.PartnerOrganization')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PCA',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('partnership_type', models.CharField(default='pd', choices=[('pd', 'Programme Document'), ('shpd', 'Simplified Humanitarian Programme Document'), ('dct', 'DCT to Government')], max_length=255, blank=True, null=True, verbose_name='Document type')),
                ('number', models.CharField(default='UNASSIGNED', help_text='PRC Reference Number', max_length=45L, blank=True)),
                ('title', models.CharField(max_length=256L)),
                ('status', models.CharField(default='in_process', help_text='In Process = In discussion with partner, Active = Currently ongoing, Implemented = completed, Cancelled = cancelled or not approved', max_length=32L, blank=True, choices=[('in_process', 'In Process'), ('active', 'Active'), ('implemented', 'Implemented'), ('cancelled', 'Cancelled')])),
                ('start_date', models.DateField(help_text='The date the partnership will start', null=True, blank=True)),
                ('end_date', models.DateField(help_text='The date the partnership will end', null=True, blank=True)),
                ('initiation_date', models.DateField(help_text='The date the partner submitted complete partnership documents to Unicef', verbose_name='Submission Date')),
                ('submission_date', models.DateField(help_text='The date the documents were submitted to the PRC', null=True, verbose_name='Submission Date to PRC', blank=True)),
                ('review_date', models.DateField(help_text='The date the PRC reviewed the partnership', null=True, verbose_name='Review date by PRC', blank=True)),
                ('signed_by_unicef_date', models.DateField(null=True, blank=True)),
                ('signed_by_partner_date', models.DateField(null=True, blank=True)),
                ('unicef_mng_first_name', models.CharField(max_length=64L, blank=True)),
                ('unicef_mng_last_name', models.CharField(max_length=64L, blank=True)),
                ('unicef_mng_email', models.CharField(max_length=128L, blank=True)),
                ('partner_mng_first_name', models.CharField(max_length=64L, blank=True)),
                ('partner_mng_last_name', models.CharField(max_length=64L, blank=True)),
                ('partner_mng_email', models.CharField(max_length=128L, blank=True)),
                ('partner_mng_phone', models.CharField(max_length=64L, blank=True)),
                ('partner_contribution_budget', models.IntegerField(default=0, null=True, blank=True)),
                ('unicef_cash_budget', models.IntegerField(default=0, null=True, blank=True)),
                ('in_kind_amount_budget', models.IntegerField(default=0, null=True, blank=True)),
                ('cash_for_supply_budget', models.IntegerField(default=0, null=True, blank=True)),
                ('total_cash', models.IntegerField(default=0, null=True, verbose_name=b'Total Budget', blank=True)),
                ('sectors', models.CharField(max_length=255, null=True, blank=True)),
                ('current', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amendment', models.BooleanField(default=False)),
                ('amended_at', models.DateTimeField(null=True)),
                ('amendment_number', models.IntegerField(default=0)),
                ('agreement', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'partner', chained_field=b'partner', blank=True, auto_choose=True, to='partners.Agreement', null=True)),
                ('original', models.ForeignKey(related_name='amendments', to='partners.PCA', null=True)),
                ('partner', models.ForeignKey(to='partners.PartnerOrganization')),
                ('partner_focal_point', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'partner', related_name='my_partnerships', chained_field=b'partner', blank=True, to='partners.PartnerStaffMember', null=True)),
                ('partner_manager', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'partner', related_name='signed_partnerships', chained_field=b'partner', verbose_name='Signed by partner', blank=True, to='partners.PartnerStaffMember', null=True)),
                ('result_structure', models.ForeignKey(blank=True, to='reports.ResultStructure', help_text='Which result structure does this partnership report under?', null=True)),
                ('unicef_manager', models.ForeignKey(related_name='approved_partnerships', verbose_name='Signed by', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('unicef_managers', models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name=b'Unicef focal points', blank=True)),
            ],
            options={
                'ordering': ['-number', 'amendment'],
                'verbose_name': 'Intervention',
                'verbose_name_plural': 'Interventions',
            },
            bases=(EquiTrack.mixins.AdminURLMixin, models.Model),
        ),
        migrations.CreateModel(
            name='PCAFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', filer.fields.file.FilerFileField(to='filer.File')),
                ('pca', models.ForeignKey(to='partners.PCA')),
                ('type', models.ForeignKey(to='partners.FileType')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PCAGrant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('funds', models.IntegerField(null=True, blank=True)),
                ('amendment', models.ForeignKey(related_name='grants', blank=True, to='partners.AmendmentLog', null=True)),
                ('grant', models.ForeignKey(to='funds.Grant')),
                ('partnership', models.ForeignKey(to='partners.PCA')),
            ],
            options={
                'ordering': ['-funds'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PCASector',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('amendment', models.ForeignKey(related_name='sectors', blank=True, to='partners.AmendmentLog', null=True)),
                ('pca', models.ForeignKey(to='partners.PCA')),
                ('sector', models.ForeignKey(to='reports.Sector')),
            ],
            options={
                'verbose_name': 'PCA Sector',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PCASectorActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('activity', models.ForeignKey(to='reports.Activity')),
                ('pca_sector', models.ForeignKey(to='partners.PCASector')),
            ],
            options={
                'verbose_name': 'Activity',
                'verbose_name_plural': 'Activities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PCASectorGoal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('goal', models.ForeignKey(to='reports.Goal')),
                ('pca_sector', models.ForeignKey(to='partners.PCASector')),
            ],
            options={
                'verbose_name': 'CCC',
                'verbose_name_plural': 'CCCs',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PCASectorImmediateResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Intermediate_result', models.ForeignKey(to='reports.IntermediateResult')),
                ('pca_sector', models.ForeignKey(to='partners.PCASector')),
                ('wbs_activities', models.ManyToManyField(to='reports.WBS')),
            ],
            options={
                'verbose_name': 'Intermediate Result',
                'verbose_name_plural': 'Intermediate Results',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PCASectorOutput',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('output', models.ForeignKey(to='reports.Rrp5Output')),
                ('pca_sector', models.ForeignKey(to='partners.PCASector')),
            ],
            options={
                'verbose_name': 'Output',
                'verbose_name_plural': 'Outputs',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Recommendation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subject_area', models.CharField(max_length=50, choices=[('partner', 'Implementing Partner'), ('funds', 'Funds Flow'), ('staff', 'Staffing'), ('policy', 'Acct Policies & Procedures'), ('int-audit', 'Internal Audit'), ('ext-audit', 'External Audit'), ('reporting', 'Reporting and Monitoring'), ('systems', 'Information Systems')])),
                ('description', models.CharField(max_length=254)),
                ('level', models.CharField(max_length=50, verbose_name='Priority Flag', choices=[('high', 'High'), ('significant', 'Significant'), ('moderate', 'Moderate'), ('low', 'Low')])),
                ('closed', models.BooleanField(default=False, verbose_name='Closed?')),
                ('completed_date', models.DateField(null=True, blank=True)),
                ('assessment', models.ForeignKey(to='partners.Assessment')),
            ],
            options={
                'verbose_name': 'Key recommendation',
                'verbose_name_plural': 'Key recommendations',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResultChain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('target', models.PositiveIntegerField(null=True, blank=True)),
                ('governorate', models.ForeignKey(blank=True, to='locations.Governorate', null=True)),
                ('indicator', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'result', chained_field=b'result', blank=True, auto_choose=True, to='reports.Indicator', null=True)),
                ('partnership', models.ForeignKey(related_name='results', to='partners.PCA')),
                ('result', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'result_type', to='reports.Result', chained_field=b'result_type')),
                ('result_type', models.ForeignKey(to='reports.ResultType')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SupplyPlan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('quantity', models.PositiveIntegerField(help_text='Total quantity needed for this intervention')),
                ('item', models.ForeignKey(to='supplies.SupplyItem')),
                ('partnership', models.ForeignKey(related_name='supply_plans', to='partners.PCA')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='partnershipbudget',
            name='partnership',
            field=models.ForeignKey(related_name='budget_log', to='partners.PCA'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='indicatorprogress',
            name='pca_sector',
            field=models.ForeignKey(to='partners.PCASector'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gwpcalocation',
            name='pca',
            field=models.ForeignKey(related_name='locations', to='partners.PCA'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gwpcalocation',
            name='region',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'governorate', chained_field=b'governorate', auto_choose=True, to='locations.Region'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gwpcalocation',
            name='sector',
            field=models.ForeignKey(blank=True, to='reports.Sector', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='distributionplan',
            name='partnership',
            field=models.ForeignKey(related_name='distribution_plans', to='partners.PCA'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='authorizedofficer',
            name='officer',
            field=models.ForeignKey(to='partners.PartnerStaffMember'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assessment',
            name='partner',
            field=models.ForeignKey(to='partners.PartnerOrganization'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assessment',
            name='requesting_officer',
            field=models.ForeignKey(related_name='requested_assessments', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='amendmentlog',
            name='partnership',
            field=models.ForeignKey(related_name='amendments_log', to='partners.PCA'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='agreement',
            name='partner',
            field=models.ForeignKey(to='partners.PartnerOrganization'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='agreement',
            name='partner_manager',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'partner', chained_field=b'partner', verbose_name='Signed by partner', blank=True, to='partners.PartnerStaffMember', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='agreement',
            name='signed_by',
            field=models.ForeignKey(related_name='signed_pcas', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
