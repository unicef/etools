from .models import Permission
from .utils import collect_parent_models


def has_action_permission(action):
    def has_perm(instance, user):
        models = collect_parent_models(instance._meta.model)
        targets = map(lambda model: Permission.get_target(model, action), models)

        context = getattr(user, '_permission_context', [])

        permissions = Permission.objects.filter_by_context(context) \
            .filter_by_targets(targets).filter(permission=Permission.PERMISSIONS.action)

        return bool(
            Permission.apply_permissions(permissions, targets, Permission.PERMISSIONS.action)
        )

    return has_perm
