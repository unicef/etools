from rest_framework.permissions import BasePermission


class UserWithName(BasePermission):
    """
    Allows access only to user with specific name.
    """
    name = ''

    def has_permission(self, request, view):
        return request.user and request.user.first_name == self.name


class UserIsBobPermission(UserWithName):
    name = 'Bob'


class UserIsAlicePermission(UserWithName):
    name = 'Alice'
