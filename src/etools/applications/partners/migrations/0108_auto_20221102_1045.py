# Generated by Django 3.2.6 on 2022-11-02 10:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import etools.applications.partners.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('partners', '0107_alter_partnerorganization_organization'),
    ]

    operations = [
        # on FK field renaming, the old indexes are not renamed, so first drop them to avoid name collision
        # https://code.djangoproject.com/ticket/23577
        migrations.AlterField(
            model_name='agreement',
            name='partner_manager',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agreements_signed', to='partners.partnerstaffmember', verbose_name='Signed by partner'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='partner_authorized_officer_signatory',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='signed_interventions', to='partners.partnerstaffmember', verbose_name='Signed by Partner'),
        ),
        migrations.AlterField(
            model_name='interventionamendment',
            name='partner_authorized_officer_signatory',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='partners.partnerstaffmember', verbose_name='Signed by Partner'),
        ),
        migrations.RenameField(
            model_name='agreement',
            old_name='authorized_officers',
            new_name='old_authorized_officers',
        ),
        migrations.RenameField(
            model_name='intervention',
            old_name='partner_focal_points',
            new_name='old_partner_focal_points',
        ),
        migrations.RenameField(
            model_name='agreement',
            old_name='partner_manager',
            new_name='old_partner_manager',
        ),
        migrations.RenameField(
            model_name='intervention',
            old_name='partner_authorized_officer_signatory',
            new_name='old_partner_authorized_officer_signatory',
        ),
        migrations.RenameField(
            model_name='interventionamendment',
            old_name='partner_authorized_officer_signatory',
            new_name='old_partner_authorized_officer_signatory',
        ),
        migrations.AddField(
            model_name='agreement',
            name='temp_authorized_officers',
            field=models.ManyToManyField(blank=True, related_name='agreement_authorizations', to=settings.AUTH_USER_MODEL, verbose_name='Partner Authorized Officer'),
        ),
        migrations.AddField(
            model_name='intervention',
            name='temp_partner_focal_points',
            field=models.ManyToManyField(blank=True, related_name='_partners_intervention_partner_focal_points_+', to=settings.AUTH_USER_MODEL, verbose_name='CSO Authorized Officials'),
        ),
        migrations.AddField(
            model_name='agreement',
            name='partner_manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agreements_signed', to=settings.AUTH_USER_MODEL, verbose_name='Signed by partner'),
        ),
        migrations.AddField(
            model_name='intervention',
            name='partner_authorized_officer_signatory',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='signed_interventions', to=settings.AUTH_USER_MODEL, verbose_name='Signed by Partner'),
        ),
        migrations.AddField(
            model_name='interventionamendment',
            name='partner_authorized_officer_signatory',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Signed by Partner'),
        ),
        # https://docs.djangoproject.com/en/3.2/topics/migrations/#historical-models
        # to be able to access model.objects in migrations
        migrations.AlterModelManagers(
            name='agreement',
            managers=[
                ('view_objects', django.db.models.manager.Manager()),
                ('objects', etools.applications.partners.models.MainAgreementManager()),
            ],
        ),
        # change verbose name on old_ fields
        migrations.AlterField(
            model_name='agreement',
            name='old_authorized_officers',
            field=models.ManyToManyField(blank=True, related_name='agreement_authorizations', to='partners.PartnerStaffMember', verbose_name='(old)Partner Authorized Officer'),
        ),
        migrations.AlterField(
            model_name='agreement',
            name='old_partner_manager',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agreements_signed', to='partners.partnerstaffmember', verbose_name='(old)Signed by partner'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='old_partner_authorized_officer_signatory',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='signed_interventions', to='partners.partnerstaffmember', verbose_name='(old)Signed by Partner'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='old_partner_focal_points',
            field=models.ManyToManyField(blank=True, related_name='_partners_intervention_old_partner_focal_points_+', to='partners.PartnerStaffMember', verbose_name='(old)CSO Authorized Officials'),
        ),
        migrations.AlterField(
            model_name='interventionamendment',
            name='old_partner_authorized_officer_signatory',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='partners.partnerstaffmember', verbose_name='(old)Signed by Partner'),
        ),
        migrations.AlterField(
            model_name='partnerstaffmember',
            name='partner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='old_staff_members', to='partners.partnerorganization', verbose_name='Partner'),
        ),
        migrations.AlterField(
            model_name='partnerstaffmember',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='old_partner_staff_member', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
    ]