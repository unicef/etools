from etools.applications.field_monitoring.groups import FMUser
from etools.applications.permissions_simplified.permissions import UserInGroup


class UserIsFieldMonitor(UserInGroup):
    group = FMUser.name
