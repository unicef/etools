from .models import Permission


def has_action_permission(action):
    def has_perm(instance, user):
        target = Permission.get_target(instance, action)
        context = getattr(user, '_permission_context', [])

        permissions = Permission.objects.filter_by_context(context) \
            .filter_by_targets([target]).filter(permission=Permission.PERMISSIONS.action)

        return bool(
            Permission.apply_permissions(permissions, [target], Permission.PERMISSIONS.action)
        )

    return has_perm
