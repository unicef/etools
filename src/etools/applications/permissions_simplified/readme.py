"""
Simple permissions which are calculated on view level with FSM support & proper work with metadata.

Process flow:

0. If view has parent, run 1-3 for it and if we are not allowed to edit, we can't make any changes to children.

1. Check if user has write access to the objects in common: ask `.has_permission()`
for every definition in write_permission_classes.

2. If instance provided, also check `.has_object_permission()` for write_permission_classes.

3. Set read_only flag to the serializer based on two previous results.
This notify serializer, there are no writable fields and protect instance from being edited.

4. If method is not safe, i.e. not in ('GET', 'HEAD', 'OPTIONS'), while write access is not granted,
raise permission denied error.



To make permissions definitions easier, PermissionQ wrapper was implemented which allow permissions
act together & create complex logic using basic logic operations: AND, OR, NOT
similarly to models.Q in queryset: .filter(Q(date__gt=now) | Q(date__isnull=True))
By default, rest framework allow AND (user is allowed, if all permissions are satisfied). But it's not flexible enough.
So, instead of writing complex permissions with duplicated logic like IsPMEOrAuthor, IsPMEOrFocalPoint,
we can write simple basic nodes & combine them:

IsPMEOrAuthor -> PermissionQ(IsPME) | PermissionQ(IsAuthor)
IsPMEOrFocalPoint -> PermissionQ(IsPME) | PermissionQ(IsFocalPoint)

For more examples, see test application.
"""
