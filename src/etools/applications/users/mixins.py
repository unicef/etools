from django.contrib.auth.models import Group


class AMPGroupsAllowedMixin:
    groups_allowed_editing = []

    GROUPS_ALLOWED_MAP = {
        "IP Editor": ["IP Viewer"],
        "IP Admin": ["IP Viewer", "IP Editor", "IP Authorized Officer"],
        "IP Authorized Officer": ["IP Viewer", "IP Editor", "IP Authorized Officer"],
        "UNICEF User:": [],
        "PME": [],
        "Partnership Manager": ["IP Viewer", "IP Editor", "IP Authorized Officer"],
        "UNICEF Audit Focal Point": ["Auditor"],
    }

    def get_user_allowed_groups(self, user=None):
        if not user:
            user = self.request.user
        amp_groups = user.groups.filter(name__in=self.GROUPS_ALLOWED_MAP.keys()).values_list('name', flat=True)
        for amp_group in amp_groups:
            self.groups_allowed_editing.extend(self.GROUPS_ALLOWED_MAP.get(amp_group))
        return Group.objects.filter(name__in=list(set(self.groups_allowed_editing)))
