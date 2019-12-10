from etools.applications.field_monitoring.groups import FMUser
from etools.applications.tpm.models import PME


def user_is_field_monitor_permission(activity, user):
    if {FMUser.as_group(), PME.as_group()}.intersection(user.groups.all()):
        return True
    return False


def user_is_person_responsible_permission(activity, user):
    return user == activity.person_responsible
