from rest_framework.permissions import IsAuthenticated


class IsInSchema(IsAuthenticated):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        # make sure user has schema/tenant set
        return bool(hasattr(request, "tenant") and request.tenant)
