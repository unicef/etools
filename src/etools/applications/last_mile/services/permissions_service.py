from django.contrib.auth.models import Permission

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
        for perm_codename in LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                if not user.user_permissions.filter(id=perm.id).exists():
                    user.user_permissions.add(perm)
            except Permission.DoesNotExist:
                pass

    def assign_permissions_for_hq_admin(self, user):
        for perm_codename in LIST_INTERESTED_LASTMILE_PERMS:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                if not user.user_permissions.filter(id=perm.id).exists():
                    user.user_permissions.add(perm)
            except Permission.DoesNotExist:
                pass

    def handle_realm_save_permissions(self, realm_instance, created=False):
        if realm_instance.group.name not in [self.LMSM_CO_ADMIN, self.LMSM_HQ_ADMIN]:
            return False

        if realm_instance.is_active:
            if realm_instance.group.name == self.LMSM_CO_ADMIN:
                self.assign_permissions_for_co_admin(realm_instance.user)
                return True
            elif realm_instance.group.name == self.LMSM_HQ_ADMIN:
                self.assign_permissions_for_hq_admin(realm_instance.user)
                return True
        else:
            return self.handle_realm_removal_permissions(realm_instance)

        return False

    def handle_realm_deletion_permissions(self, realm_instance):
        return self.handle_realm_removal_permissions(realm_instance)

    def handle_realm_removal_permissions(self, realm_instance):

        if realm_instance.group.name not in [self.LMSM_CO_ADMIN, self.LMSM_HQ_ADMIN]:
            return False

        has_co_admin = Realm.objects.filter(
            user=realm_instance.user,
            group__name=self.LMSM_CO_ADMIN,
            is_active=True
        ).exists()

        has_hq_admin = Realm.objects.filter(
            user=realm_instance.user,
            group__name=self.LMSM_HQ_ADMIN,
            is_active=True
        ).exists()

        if not has_co_admin and not has_hq_admin:
            self.remove_all_lmsm_permissions(realm_instance.user)
        elif has_co_admin and not has_hq_admin:
            self.remove_approve_permissions(realm_instance.user)

        return True

    def remove_all_lmsm_permissions(self, user):
        for perm_codename in LIST_INTERESTED_LASTMILE_PERMS:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                user.user_permissions.remove(perm)
            except Permission.DoesNotExist:
                pass

    def remove_approve_permissions(self, user):
        approve_perms = set(LIST_INTERESTED_LASTMILE_PERMS) - set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)

        for perm_codename in approve_perms:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                user.user_permissions.remove(perm)
            except Permission.DoesNotExist:
                pass

    def is_lmsm_admin_group(self, group_name):
        return group_name in self.LMSM_GROUPS
