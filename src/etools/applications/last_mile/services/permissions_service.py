from django.contrib.auth.models import Group, Permission

from etools.applications.last_mile.admin_panel.constants import (
    LIST_INTERESTED_LASTMILE_PERMS,
    LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE,
)
from etools.applications.users.models import Realm


class LMSMPermissionsService:

    LMSM_CO_ADMIN = "LMSM CO Admin"
    LMSM_HQ_ADMIN = "LMSM HQ Admin"
    LMSM_ADMIN_PANEL = "LMSM Admin Panel"
    IP_LM_EDITOR = "IP LM Editor"
    LMSMAPI = "LMSMApi"
    IP_LM_VIEWR = "IP LM Viewer"
    LMSM_GROUPS = [LMSM_CO_ADMIN, LMSM_HQ_ADMIN, IP_LM_EDITOR, LMSMAPI, IP_LM_VIEWR, LMSM_ADMIN_PANEL]

    def assign_permissions_for_co_admin(self, user):
        permissions = Permission.objects.filter(codename__in=LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)
        if permissions:
            user.user_permissions.add(*permissions)

    def assign_permissions_for_hq_admin(self, user):
        permissions = Permission.objects.filter(codename__in=LIST_INTERESTED_LASTMILE_PERMS)
        if permissions:
            user.user_permissions.add(*permissions)

    def assign_lmsm_admin_panel_group(self, user, country, organization):
        try:
            admin_panel_group = Group.objects.get(name=self.LMSM_ADMIN_PANEL)
            realm, created = Realm.objects.get_or_create(
                user=user,
                country=country,
                organization=organization,
                group=admin_panel_group,
                defaults={'is_active': True}
            )

            if not created and not realm.is_active:
                realm.is_active = True
                realm.save(update_fields=['is_active'])
        except Group.DoesNotExist:
            # LMSM Admin Panel group doesn't exist, skip
            pass

    def handle_realm_save_permissions(self, realm_instance):
        if realm_instance.group.name not in [self.LMSM_CO_ADMIN, self.LMSM_HQ_ADMIN]:
            return False

        if realm_instance.is_active:
            if realm_instance.group.name == self.LMSM_CO_ADMIN:
                self.assign_permissions_for_co_admin(realm_instance.user)
                self.assign_lmsm_admin_panel_group(
                    realm_instance.user,
                    realm_instance.country,
                    realm_instance.organization
                )
                return True
            elif realm_instance.group.name == self.LMSM_HQ_ADMIN:
                self.assign_permissions_for_hq_admin(realm_instance.user)
                self.assign_lmsm_admin_panel_group(
                    realm_instance.user,
                    realm_instance.country,
                    realm_instance.organization
                )
                return True
        else:
            return self.handle_realm_removal_permissions(realm_instance)

        return False

    def handle_realm_deletion_permissions(self, realm_instance):
        return self.handle_realm_removal_permissions(realm_instance)

    def handle_realm_removal_permissions(self, realm_instance):

        if realm_instance.group.name not in [self.LMSM_CO_ADMIN, self.LMSM_HQ_ADMIN]:
            return False

        # Check remaining groups for the same country and organization (single query)
        remaining_country_groups = set(Realm.objects.filter(
            user=realm_instance.user,
            country=realm_instance.country,
            organization=realm_instance.organization,
            group__name__in=[self.LMSM_CO_ADMIN, self.LMSM_HQ_ADMIN],
            is_active=True
        ).exclude(pk=realm_instance.pk).values_list('group__name', flat=True))

        # If no CO or HQ admin groups remain for this country, remove LMSM Admin Panel for this country
        if not remaining_country_groups:
            self.remove_lmsm_admin_panel_group(realm_instance.user, realm_instance.country, realm_instance.organization)

        # Now check globally across all countries for permissions management (single query)
        remaining_global_groups = set(Realm.objects.filter(
            user=realm_instance.user,
            group__name__in=[self.LMSM_CO_ADMIN, self.LMSM_HQ_ADMIN],
            is_active=True
        ).exclude(pk=realm_instance.pk).values_list('group__name', flat=True))

        has_co_admin_global = self.LMSM_CO_ADMIN in remaining_global_groups
        has_hq_admin_global = self.LMSM_HQ_ADMIN in remaining_global_groups

        if not has_co_admin_global and not has_hq_admin_global:
            self.remove_all_lmsm_permissions(realm_instance.user)
        elif has_co_admin_global and not has_hq_admin_global:
            self.remove_approve_permissions(realm_instance.user)

        return True

    def remove_lmsm_admin_panel_group(self, user, country, organization):
        try:
            admin_panel_group = Group.objects.get(name=self.LMSM_ADMIN_PANEL)
            updated = Realm.objects.filter(
                user=user,
                country=country,
                organization=organization,
                group=admin_panel_group,
                is_active=True
            ).update(is_active=False)

            return updated > 0
        except Group.DoesNotExist:
            return False

    def remove_all_lmsm_permissions(self, user):
        permissions = Permission.objects.filter(codename__in=LIST_INTERESTED_LASTMILE_PERMS)

        if permissions.exists():
            user.user_permissions.remove(*permissions)

    def remove_approve_permissions(self, user):
        approve_perms = set(LIST_INTERESTED_LASTMILE_PERMS) - set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)
        permissions = Permission.objects.filter(codename__in=approve_perms)
        if permissions.exists():
            user.user_permissions.remove(*permissions)

    def is_lmsm_admin_group(self, group_name):
        return group_name in self.LMSM_GROUPS
