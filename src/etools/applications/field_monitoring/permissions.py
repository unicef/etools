from etools.applications.field_monitoring.groups import FMUser, PME
from etools.applications.permissions_simplified.permissions import UserInGroup, PermissionQ


class IsFMUser(UserInGroup):
    group = FMUser.name


class IsPME(UserInGroup):
    group = PME.name


UserIsFieldMonitor = PermissionQ(IsFMUser) | PermissionQ(IsPME)
