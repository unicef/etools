# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('partners', '0002_initial'),
        ('psea', '0002_assessor_auditor_firm'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessor',
            name='auditor_firm_staff',
            field=models.ManyToManyField(blank=True, related_name='_psea_assessor_auditor_firm_staff_+', to=settings.AUTH_USER_MODEL, verbose_name='Auditor Staff'),
        ),
        migrations.AddField(
            model_name='assessor',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='assessmentstatushistory',
            name='assessment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='psea.assessment', verbose_name='Assessment'),
        ),
        migrations.AddField(
            model_name='assessment',
            name='focal_points',
            field=models.ManyToManyField(blank=True, related_name='pse_assessment_focal_point', to=settings.AUTH_USER_MODEL, verbose_name='UNICEF Focal Points'),
        ),
        migrations.AddField(
            model_name='assessment',
            name='partner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='psea_assessment', to='partners.partnerorganization', verbose_name='Partner'),
        ),
        migrations.AddField(
            model_name='answerevidence',
            name='answer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evidences', to='psea.answer', verbose_name='Answer'),
        ),
        migrations.AddField(
            model_name='answerevidence',
            name='evidence',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='psea.evidence', verbose_name='Evidence'),
        ),
        migrations.AddField(
            model_name='answer',
            name='assessment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='psea.assessment', verbose_name='Assessment'),
        ),
        migrations.AddField(
            model_name='answer',
            name='indicator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='psea.indicator', verbose_name='Indicator'),
        ),
        migrations.AddField(
            model_name='answer',
            name='rating',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='psea.rating', verbose_name='Rating'),
        ),
        migrations.AlterUniqueTogether(
            name='answer',
            unique_together={('assessment', 'indicator')},
        ),
    ]