# Generated by Django 3.2.6 on 2022-08-18 09:37
import sys
import logging

from django.db import migrations, transaction, connection, models


def get_user_profile(apps, user, no_profile):
    UserProfile = apps.get_model('users', 'UserProfile')

    if not hasattr(user, 'profile'):
        no_profile += 1
        logging.warning(f"User {user.id}: {user.username} has no profile. "
                        f"Adding a user profile..")
        return UserProfile.objects.create(user=user)
    return user.profile


def get_user_countries(apps, profile, uat_country):
    Country = apps.get_model('users', 'Country')
    filters = models.Q()
    if profile.country:
        filters |= models.Q(id=profile.country.id)
    if profile.country_override:
        filters |= models.Q(id=profile.country_override.id)
    if profile.countries_available.exists():
        filters |= models.Q(id__in=profile.countries_available.values_list('pk', flat=True))

    countries_qs = Country.objects \
        .filter(filters) \
        .exclude(name__in=['Global'])

    if not filters:
        # If the user has no country set, add UAT to country and deactivate the user..")
        profile.country_override = uat_country
        profile.save(update_fields=['country_override'])
        profile.countries_available.add(uat_country)

        profile.user.is_active = False
        profile.user.save(update_fields=['is_active'])

        return Country.objects.filter(id=uat_country.id), True
    return countries_qs, False


def fwd_migrate_to_user_realms(apps, schema_editor):
    # Don't run migration when testing
    if "test" in sys.argv:
        return
    User = apps.get_model('users', 'User')
    Realm = apps.get_model('users', 'Realm')
    Country = apps.get_model('users', 'Country')
    Group = apps.get_model('auth', 'Group')
    Organization = apps.get_model('organizations', 'Organization')

    with transaction.atomic():
        no_profile, no_countries, no_realms = 0, 0, 0
        unicef_org, _ = Organization.objects.get_or_create(
            name='UNICEF',
            vendor_number='UNICEF',
            defaults={
                'organization_type': 'UN Agency',
                'cso_type': 'International'
            }
        )
        external_psea_org, _ = Organization.objects.get_or_create(
            name='EXTERNAL PSEA ASSESSORS',
            vendor_number='EXTERNAL PSEA ASSESSORS',
        )
        uat_country = Country.objects.get(name='UAT')

        unicef_user_group, _ = Group.objects.get_or_create(name="UNICEF User")
        external_psea_group, _ = Group.objects.get_or_create(name="PSEA Assessor")
        auditor_group, _ = Group.objects.get_or_create(name="Auditor")
        tpm_group, _ = Group.objects.get_or_create(name="Third Party Monitor")
        ip_viewer_group, _ = Group.objects.get_or_create(name="IP Viewer")

        logging.info(f'Processing {User.objects.count()} users..')

        for user in User.objects.all() \
                .select_related('profile', 'profile__country', 'profile__country_override',
                                'purchase_order_auditorstaffmember',
                                'tpmpartners_tpmpartnerstaffmember') \
                .prefetch_related('groups', 'profile__countries_available'):

            profile = get_user_profile(apps, user, no_profile)
            countries, added_uat = get_user_countries(apps, profile, uat_country)
            if added_uat:
                no_countries += 1
            user.refresh_from_db()

            groups = user.groups.all()
            is_unicef_user = groups.filter(name__contains='UNICEF').count() > 0 or 'unicef' in user.email
            auditor_staff = hasattr(user, 'purchase_order_auditorstaffmember') and user.purchase_order_auditorstaffmember
            tpm_staff = hasattr(user, 'tpmpartners_tpmpartnerstaffmember') and user.tpmpartners_tpmpartnerstaffmember

            realm_list = []

            if is_unicef_user:
                for country in countries:
                    if groups.exists():
                        for group in groups:
                            realm_list.append(dict(
                                user_id=user.id,
                                country_id=country.id,
                                organization_id=unicef_org.id,
                                group_id=group.id,
                                is_active=user.is_active
                            ))
                    # if unicef user has no groups, set UNICEF User group
                    else:
                        realm_list.append(dict(
                            user_id=user.id,
                            country_id=country.id,
                            organization_id=unicef_org.id,
                            group_id=unicef_user_group.id,
                            is_active=user.is_active
                        ))

            if auditor_staff:
                auditor_organization = auditor_staff.auditor_firm.organization
                if not auditor_organization:
                    logging.info(
                        f"Auditor Firm with id:{auditor_staff.auditor_firm.id} for staff user {user.id} "
                        f"has no organization set. Skipping..")
                else:
                    for country in countries:
                        if groups.exists():
                            for group in groups:
                                realm_list.append(dict(
                                    user_id=user.id,
                                    country_id=country.id,
                                    organization_id=auditor_organization.id,
                                    group_id=group.id,
                                    is_active=not auditor_staff.hidden
                                ))
                            # add Auditor group for the case when user is an auditor staff,
                            # but the Auditor group is not set
                            if auditor_group not in groups:
                                realm_list.append(dict(
                                    user_id=user.id,
                                    country_id=country.id,
                                    organization_id=auditor_organization.id,
                                    group_id=auditor_group.id,
                                    is_active=not auditor_staff.hidden
                                ))
                        # if audit staff member has no groups, add Auditor group
                        else:
                            realm_list.append(dict(
                                user_id=user.id,
                                country_id=country.id,
                                organization_id=auditor_organization.id,
                                group_id=auditor_group.id,
                                is_active=user.is_active
                            ))

            if tpm_staff:
                tpm_organization = tpm_staff.tpm_partner.organization
                if not tpm_organization:
                    logging.info(
                        f"TPM Partner with id:{tpm_staff.tpm_partner.id} for staff user {user.id} "
                        f"has no organization set. Skipping..")
                else:
                    for country in countries:
                        if groups.exists():
                            for group in groups:
                                realm_list.append(dict(
                                    user_id=user.id,
                                    country_id=country.id,
                                    organization_id=tpm_organization.id,
                                    group_id=group.id,
                                    is_active=user.is_active
                                ))
                            # add Third Party Monitor group for the case when user is an tpm staff,
                            # but the Third Party Monitor group is not set
                            if tpm_group not in groups:
                                realm_list.append(dict(
                                    user_id=user.id,
                                    country_id=country.id,
                                    organization_id=tpm_organization.id,
                                    group_id=tpm_group.id,
                                    is_active=user.is_active
                                ))
                        # if TPM staff member has no group set, add Third Party Monitor group
                        else:
                            realm_list.append(dict(
                                user_id=user.id,
                                country_id=country.id,
                                organization_id=tpm_organization.id,
                                group_id=tpm_group.id,
                                is_active=user.is_active
                            ))
            # check if user is a partner staff member for each country tenant
            for country in countries:
                connection.set_tenant(country)
                if hasattr(user, 'partner_staff_member') and user.partner_staff_member:
                    partner_staff = user.partner_staff_member
                    if not partner_staff.partner.organization:
                        logging.info(
                            f"Partner with id:{partner_staff.partner.id} for staff user {user.id} "
                            f"has no organization set. Skipping..")
                        continue
                    if groups.exists():
                        for group in groups:
                            realm_list.append(dict(
                                user_id=user.id,
                                country_id=country.id,
                                organization_id=partner_staff.partner.organization.id,
                                group_id=group.id,
                                is_active=partner_staff.active
                            ))
                    # if partner staff member has no groups, add IP Viewer group
                    else:
                        realm_list.append(dict(
                            user_id=user.id,
                            country_id=country.id,
                            organization_id=partner_staff.partner.organization.id,
                            group_id=ip_viewer_group.id,
                            is_active=partner_staff.active
                        ))
                elif not any([is_unicef_user, auditor_staff, tpm_staff]):
                    realm_list.append(dict(
                        user_id=user.id,
                        country_id=country.id,
                        organization_id=external_psea_org.id,
                        group_id=external_psea_group.id,
                        is_active=user.is_active
                    ))

            # switch back to public schema
            connection.set_schema_to_public()

            if not realm_list:
                logging.info(f'No realms available for user {user.id} on country: '
                             f'{profile.country.name or profile.country_override.name}')
                no_realms += 1
            else:
                unique_realms = [dict(t) for t in {tuple(sorted(d.items())) for d in realm_list}]
                Realm.objects.bulk_create([Realm(**realm_dict) for realm_dict in unique_realms])

                # update user profile with organization from last realm
                profile.organization = Organization.objects.get(id=unique_realms[-1]['organization_id'])
                profile.save(update_fields=['organization'])

        logging.info(f'{no_realms} users had no realms created because they are on Global country '
                     f'or the organization of the partner where is staff is None - no vendor_number')
        logging.info(f'{no_profile} users had no profile.')
        logging.info(f'{no_countries} users that had no countries set, were added to UAT.')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_realms'),
    ]

    operations = [
        migrations.RunPython(fwd_migrate_to_user_realms, migrations.RunPython.noop),

        migrations.RenameField(
            model_name='user',
            old_name='groups',
            new_name='old_groups',
        ),
        migrations.AlterField(
            model_name='user',
            name='old_groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='Old Groups'),
        ),
        migrations.RenameField(
            model_name='userprofile',
            old_name='countries_available',
            new_name='old_countries_available',
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='old_countries_available',
            field=models.ManyToManyField(blank=True, related_name='accessible_by', to='users.Country', verbose_name='Old Countries Available'),
        ),
    ]