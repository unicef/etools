# Generated by Django 3.2.6 on 2022-08-03 14:25
import logging

from django.conf import settings
from django.db import migrations, models, connection, transaction
import django.utils.timezone
import model_utils.fields


def migrate_to_user_realms(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Realm = apps.get_model('users', 'Realm')
    Country = apps.get_model('users', 'Country')
    Organzation = apps.get_model('organizations', 'Organization')
    PartnerStaffMember = apps.get_model('partners', 'PartnerStaffMember')

    with transaction.atomic():
        if connection.tenant.schema_name != 'public':
            return
        no_profile, no_countries = 0, 0

        unicef_org = Organzation.objects.get(name='UNICEF')
        external_psea_org = Organzation.objects.get(name='EXTERNAL PSEA ASSESSORS')

        logging.info(f'Processing {User.objects.count()} users..')

        for user in User.objects.all() \
                .select_related('profile') \
                .prefetch_related('groups', 'profile__countries_available'):
            if not hasattr(user, 'profile'):
                no_profile += 1
                logging.error(f"User {user.pk} has no profile. Skipping..")
                continue

            all_user_countries = {
                getattr(user.profile.country, 'pk', None),
                getattr(user.profile.country_override, 'pk', None)
            }
            all_user_countries.update(user.profile.countries_available.values_list('pk', flat=True))
            all_user_countries = list(filter(lambda x: x is not None, all_user_countries))
            if not all_user_countries:
                no_countries += 1
                continue
            realm_countries = Country.objects \
                .filter(id__in=all_user_countries) \
                .exclude(name__in=['Global'])

            for country in realm_countries:
                groups = user.groups.all()

                if not groups:
                    # if the user has no groups set and email domain is 'unicef'
                    if 'unicef' in user.email:
                        realm = Realm(
                            user=user,
                            country=country,
                            organization=unicef_org,
                            is_active=user.is_active
                        )
                    else:
                        realm = Realm(
                            user=user,
                            country=country,
                            organization=external_psea_org,  # TDB
                            is_active=user.is_active
                        )
                    realm.save()

                for group in groups:
                    if 'UNICEF' in group.name:
                        realm = Realm(
                            user=user,
                            country=country,
                            organization=unicef_org,
                            group=group,
                            is_active=user.is_active
                        )
                    else:
                        connection.set_tenant(country)
                        try:
                            partner_staff = PartnerStaffMember.objects \
                                .select_related('partner') \
                                .select_related('partner__organization') \
                                .get(email=user.email)
                            if not partner_staff.partner.organization:
                                logging.error(
                                    f"Partner with id:{partner_staff.partner.pk} has no organization set. Skipping..")
                                continue
                            realm = Realm(
                                user=user,
                                country=country,
                                organization=partner_staff.partner.organization,
                                group=group, is_active=user.is_active
                            )
                        except PartnerStaffMember.DoesNotExist:
                            if 'unicef' in user.email:
                                realm = Realm(
                                    user=user,
                                    country=country,
                                    organization=unicef_org,
                                    group=group,
                                    is_active=user.is_active
                                )
                            else:
                                realm = Realm(
                                    user=user,
                                    country=country,
                                    organization=external_psea_org,
                                    group=group,
                                    is_active=user.is_active
                                )
                    realm.save()

        logging.info(f'{no_profile} users had no profile.')
        logging.info(f'{no_countries} users had no countries set on profile.')


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('organizations', '0001_initial'),
        ('users', '0018_merge_20220511_1411'),
    ]

    operations = [
        migrations.CreateModel(
            name='Realm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.country', verbose_name='Country')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='auth.group', verbose_name='Group')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organizations.organization', verbose_name='Organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Realm',
                'verbose_name_plural': 'Realms',
            },
        ),
        migrations.AddConstraint(
            model_name='realm',
            constraint=models.UniqueConstraint(fields=('user', 'country', 'organization', 'group'), name='unique_realm'),
        ),
        migrations.RunPython(migrate_to_user_realms, migrations.RunPython.noop)
    ]

