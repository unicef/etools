from django.contrib.auth.models import Group

PARTNER_ACTIVE_GROUPS = ["IP Viewer", "IP Editor", "IP Authorized Officer", "IP Admin"]
# todo: create single source of truth here and for wrappers like tpm.models.ThirdPartyMonitor. GroupWrapper for caching
AUDIT_ACTIVE_GROUPS = ["UNICEF Audit Focal Point", "Auditor"]
TPM_ACTIVE_GROUPS = ["Third Party Monitor"]


ORGANIZATION_GROUP_MAP = {
    "audit": ['Auditor'],
    "partner": PARTNER_ACTIVE_GROUPS,
    "tpm": TPM_ACTIVE_GROUPS,
}


class GroupEditPermissionMixin:

    GROUPS_ALLOWED_MAP = {
        "IP Editor": {"partner": ["IP Viewer"]},
        "IP Admin": {"partner": ["IP Viewer", "IP Editor", "IP Authorized Officer"]},
        "IP Authorized Officer": {"partner": ["IP Viewer", "IP Editor", "IP Authorized Officer"]},
        "UNICEF User:": {},
        "PME": {},
        "Partnership Manager": ORGANIZATION_GROUP_MAP,
        "UNICEF Audit Focal Point": {"audit": ["Auditor"]},
    }

    CAN_ADD_USER = ["IP Admin", "IP Authorized Officer", "Partnership Manager"]

    def get_user_allowed_groups(self, organization_type, user=None):
        groups_allowed_editing = []
        if not user:
            user = self.request.user
        amp_groups = user.groups.filter(name__in=self.GROUPS_ALLOWED_MAP.keys()).values_list('name', flat=True)

        for amp_group in amp_groups:
            if organization_type and organization_type in ORGANIZATION_GROUP_MAP.keys():
                groups_allowed_editing = self.GROUPS_ALLOWED_MAP.get(amp_group).get(organization_type, [])

        return Group.objects.filter(name__in=list(set(groups_allowed_editing)))

    def can_add_user(self):
        return self.request.user.groups.filter(name__in=self.CAN_ADD_USER).exists()
