from etools.applications.permissions2.simplified.permissions import SimpleCommonPermission


class UserIsBobPermission(SimpleCommonPermission):
    """
    Allows access only to Bob.
    """

    def has_permission(self, request, view):
        return request.user and request.user.first_name == 'Bob'
