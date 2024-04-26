from django.contrib.auth.models import Group

AMP_ACTIVE_GROUPS = ["IP Viewer", "IP Editor", "IP Authorized Officer", "IP Admin", "IP LM Editor"]
PARTNER_ACTIVE_GROUPS = AMP_ACTIVE_GROUPS
# todo: create single source of truth here and for wrappers like tpm.models.ThirdPartyMonitor. GroupWrapper for caching
AUDIT_ACTIVE_GROUPS = ["UNICEF Audit Focal Point", "Auditor"]
TPM_ACTIVE_GROUPS = ["Third Party Monitor"]


ORGANIZATION_GROUP_MAP = {
    "audit": ['Auditor'],
    "partner": AMP_ACTIVE_GROUPS,
    "tpm": TPM_ACTIVE_GROUPS,
}


class GroupEditPermissionMixin:
    """
    Mixin that handles roles for editing/adding in AMP based on the authenticated user roles.
    GROUPS_ALLOWED_MAP structure:
     - the keys are used for matching the current auth user roles
     - the values {'partner': [...]} map the organization relationship_type to its specific roles:
     e.g. An authenticated IP Admin can change roles only for a partner organization,
     the roles being limited to IP Viewer, Editor, IP Authorized Officer
    """

    GROUPS_ALLOWED_MAP = {
        "IP Editor": {"partner": ["IP Viewer"]},
        "IP Admin": {"partner": ["IP Viewer", "IP Editor", "IP Authorized Officer", "IP LM Editor"]},
        "IP Authorized Officer": {"partner": ["IP Viewer", "IP Editor", "IP Authorized Officer", "IP LM Editor"]},
        "UNICEF User": {},
        "PME": {"tpm": TPM_ACTIVE_GROUPS},
        "Partnership Manager": {"partner": AMP_ACTIVE_GROUPS},
        "UNICEF Audit Focal Point": {"audit": ["Auditor"]},
    }

    CAN_ADD_USER = ["IP Admin", "IP Authorized Officer", "PME",
                    "Partnership Manager", "UNICEF Audit Focal Point"]

    CAN_REVIEW_USER = ["User Reviewer"]

    def get_user_allowed_groups(self, organization_types, user=None):
        groups_allowed_editing = []
        if not user:
            user = self.request.user

        amp_groups = user.groups.filter(name__in=self.GROUPS_ALLOWED_MAP.keys()).values_list('name', flat=True)
        if organization_types and set(organization_types).issubset(set(ORGANIZATION_GROUP_MAP.keys())):
            for amp_group in amp_groups:
                for _type in organization_types:
                    groups_allowed_editing.extend(self.GROUPS_ALLOWED_MAP.get(amp_group).get(_type, []))

        return Group.objects.filter(name__in=list(set(groups_allowed_editing)))

    def can_add_user(self):
        return self.request.user.groups.filter(name__in=self.CAN_ADD_USER).exists()

    def can_review_user(self):
        return self.request.user.groups.filter(name__in=self.CAN_REVIEW_USER).exists()
