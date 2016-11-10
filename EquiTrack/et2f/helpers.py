from __future__ import unicode_literals

from et2f import UserTypes
from et2f.models import TravelPermission


class PermissionMatrix(object):
    def __init__(self, travel, user):
        self.travel = travel
        self.user = user
        self._user_type = self.get_user_type()
        self._permission_dict = self.get_permission_dict()

    def get_user_type(self):
        return UserTypes.GOD

    def get_permission_dict(self):
        permissions = TravelPermission.objects.filter(status=self.travel.status, user_type=self._user_type)
        return {p.code: p.value for p in permissions}

    def has_permission(self, code):
        return self._permission_dict.get(code, True)