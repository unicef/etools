from rest_framework.permissions import IsAuthenticated


class IsIPLMEditor(IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.groups.filter(name='IP LM Editor').exists()
