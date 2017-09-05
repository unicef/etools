from .models import Permission
from .utils import collect_parent_models


def has_action_permission(action):
    def has_perm(instance, user):
        models = collect_parent_models(instance._meta.model)
        targets = map(lambda m: '{}.{}'.format(m._meta.model_name, action), models)
        return Permission.objects.filter(
            target__in=targets,
            permission=Permission.PERMISSIONS.action,
            permission_type=Permission.TYPES.allow
        ).filter_by_context(getattr(instance, '_permission_context', [])).exists()

    return has_perm
