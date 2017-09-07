from .models import Permission
from .utils import collect_parent_models


def has_action_permission(action):
    def has_perm(instance, user):
        models = collect_parent_models(instance._meta.model)
        targets = map(lambda m: '{}_{}.{}'.format(m._meta.app_label, m._meta.model_name, action), models)
        return Permission.objects.filter(
            target__in=targets,
            permission=Permission.PERMISSIONS.action,
            permission_type=Permission.TYPES.allow
        ).filter_by_context(getattr(user, '_permission_context', [])).exists()

    return has_perm
