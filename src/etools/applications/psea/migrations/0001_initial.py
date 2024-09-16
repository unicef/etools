# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_fsm
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('action_points', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('comments', models.TextField(blank=True, null=True, verbose_name='Comments')),
            ],
            options={
                'verbose_name': 'Answer',
                'verbose_name_plural': 'Answers',
            },
        ),
        migrations.CreateModel(
            name='AnswerEvidence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
            ],
            options={
                'verbose_name': 'Answer Evidence',
                'verbose_name_plural': 'Answer Evidences',
            },
        ),
        migrations.CreateModel(
            name='Assessment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('reference_number', models.CharField(max_length=100, unique=True, verbose_name='Reference Number')),
                ('overall_rating', models.IntegerField(blank=True, null=True)),
                ('assessment_date', models.DateField(blank=True, null=True, verbose_name='Assessment Date')),
                ('assessment_type', models.CharField(choices=[('unicef_2020', 'UNICEF Assessment 2020'), ('un_common_other', 'UN Common Assessment- Other UN'), ('un_common_unicef', 'UN Common Assessment- UNICEF')], default='unicef_2020', max_length=16)),
                ('assessment_ingo_reason', models.CharField(blank=True, choices=[('decentralized', 'Decentralization of INGO'), ('sea_allegation', 'SEA allegation'), ('global_policy_implemented', 'Global policy not being implemented at country-level'), ('high_risk_context', 'High risk context')], max_length=32, null=True)),
                ('status', django_fsm.FSMField(choices=[('draft', 'Draft'), ('assigned', 'Assigned'), ('in_progress', 'In Progress'), ('submitted', 'Submitted'), ('rejected', 'Rejected'), ('final', 'Final'), ('cancelled', 'Cancelled')], default='draft', max_length=30, verbose_name='Status')),
            ],
            options={
                'verbose_name': 'Assessment',
                'verbose_name_plural': 'Assessments',
                'ordering': ('-assessment_date',),
            },
        ),
        migrations.CreateModel(
            name='AssessmentStatusHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('assigned', 'Assigned'), ('in_progress', 'In Progress'), ('submitted', 'Submitted'), ('rejected', 'Rejected'), ('final', 'Final'), ('cancelled', 'Cancelled')], max_length=30)),
                ('comment', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'Assessment Status History',
                'verbose_name_plural': 'Assessment Status History',
                'ordering': ('-created',),
            },
        ),
        migrations.CreateModel(
            name='Evidence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('label', models.TextField(verbose_name='Label')),
                ('requires_description', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Evidence',
                'verbose_name_plural': 'Evidence',
            },
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('label', models.CharField(max_length=50, verbose_name='Label')),
                ('weight', models.IntegerField(verbose_name='Weight')),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Rating',
                'verbose_name_plural': 'Ratings',
            },
        ),
        migrations.CreateModel(
            name='AssessmentActionPoint',
            fields=[
            ],
            options={
                'verbose_name': 'PSEA Assessment Action Point',
                'verbose_name_plural': 'PSEA Assessment Action Points',
                'abstract': False,
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('action_points.actionpoint',),
        ),
        migrations.CreateModel(
            name='Indicator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False, verbose_name='order')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('subject', models.TextField(verbose_name='Subject')),
                ('content', models.TextField(verbose_name='Content')),
                ('rating_instructions', models.TextField(blank=True, verbose_name='Rating Instructions')),
                ('active', models.BooleanField(default=True)),
                ('evidences', models.ManyToManyField(to='psea.Evidence', verbose_name='Evidences')),
                ('ratings', models.ManyToManyField(to='psea.Rating', verbose_name='Rating')),
            ],
            options={
                'verbose_name': 'Indicator',
                'verbose_name_plural': 'Indicators',
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='Assessor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('assessor_type', models.CharField(choices=[('external', 'External Individual'), ('staff', 'UNICEF Staff'), ('firm', 'Assessing Firm')], max_length=30, verbose_name='Type')),
                ('order_number', models.CharField(blank=True, max_length=30, verbose_name='Order Number')),
                ('assessment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='assessor', to='psea.assessment', verbose_name='Assessment')),
            ],
            options={
                'verbose_name': 'Assessor',
                'verbose_name_plural': 'Assessors',
            },
        ),
    ]
