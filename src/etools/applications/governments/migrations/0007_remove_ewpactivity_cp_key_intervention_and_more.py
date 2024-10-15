# Generated by Django 4.2.3 on 2024-10-15 15:37

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_initial'),
        ('governments', '0006_alter_gddresultlink_cp_output'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ewpactivity',
            name='cp_key_intervention',
        ),
        migrations.RemoveField(
            model_name='ewpactivity',
            name='cp_output',
        ),
        migrations.RemoveField(
            model_name='gddkeyintervention',
            name='cp_key_intervention',
        ),
        migrations.CreateModel(
            name='EWPOutput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('cp_output', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ewp_outputs', to='reports.result')),
                ('workplan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ewp_outputs', to='governments.governmentewp', verbose_name='Workplan')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EWPKeyIntervention',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('cp_key_intervention', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ewp_key_interventions', to='reports.result')),
                ('ewp_output', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ewp_key_interventions', to='governments.ewpoutput')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='ewpactivity',
            name='ewp_key_intervention',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='ewp_activity_for_ki', to='governments.ewpkeyintervention'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='gddkeyintervention',
            name='ewp_key_intervention',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='gdd_key_interventions', to='governments.ewpkeyintervention', verbose_name='CP Key Intervention'),
        ),
        migrations.AlterField(
            model_name='gddresultlink',
            name='cp_output',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='result_links', to='governments.ewpoutput', verbose_name='CP Output'),
        ),
    ]
