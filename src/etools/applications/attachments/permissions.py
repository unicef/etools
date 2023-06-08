from rest_framework.permissions import BasePermission, IsAuthenticated

from etools.applications.core.permissions import IsUNICEFUser


class IsInSchema(IsAuthenticated):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        # make sure user has schema/tenant set
        return bool(hasattr(request, "tenant") and request.tenant)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsRelatedThirdPartyUser(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        content_object = obj.content_object
        if not content_object:
            return True

        if hasattr(content_object, 'get_related_third_party_users'):
            return content_object.get_related_third_party_users().filter(pk=request.user.pk).exists()

        return False


UNICEFAttachmentsPermission = IsInSchema & (IsUNICEFUser | IsRelatedThirdPartyUser)
