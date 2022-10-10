from django.contrib.auth.models import Group


class DynamicFieldsSerializerMixin:

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        exclude_fields = kwargs.pop('exclude_fields', None)
        read_only_fields = kwargs.pop('read_only_fields', None)
        super().__init__(*args, **kwargs)
        if fields:
            fields_to_delete = set(self.fields.keys()) - set(fields)
            for field in fields_to_delete:
                del self.fields[field]
        if exclude_fields:
            for field in exclude_fields:
                del self.fields[field]
        if read_only_fields:
            for field in read_only_fields:
                self.fields[field].read_only = True


class GroupEditPermissionMixin:

    GROUPS_ALLOWED_MAP = {
        "IP Editor": ["IP Viewer"],
        "IP Admin": ["IP Viewer", "IP Editor", "IP Authorized Officer"],
        "IP Authorized Officer": ["IP Viewer", "IP Editor", "IP Authorized Officer"],
        "UNICEF User:": [],
        "PME": [],
        "Partnership Manager": ["IP Viewer", "IP Editor", "IP Authorized Officer"],
        "UNICEF Audit Focal Point": ["Auditor"],
    }

    CAN_ADD_USER = ["IP Admin", "IP Authorized Officer"]

    def get_user_allowed_groups(self, user=None):
        groups_allowed_editing = []
        if not user:
            user = self.request.user
        amp_groups = user.groups.filter(name__in=self.GROUPS_ALLOWED_MAP.keys()).values_list('name', flat=True)
        for amp_group in amp_groups:
            groups_allowed_editing.extend(self.GROUPS_ALLOWED_MAP.get(amp_group))
        return Group.objects.filter(name__in=list(set(groups_allowed_editing)))

    def can_add_user(self):
        return self.request.user.groups.filter(name__in=self.CAN_ADD_USER).exists()
