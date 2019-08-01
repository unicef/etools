from etools.applications.field_monitoring.groups import FMUser, PME


def user_is_field_monitor_permission(activity, user):
    if {FMUser.as_group(), PME.as_group()}.intersection(user.groups.all()):
        return True
    return False


def user_is_data_collector_permission(activity, user):
    if user in activity.team_members.all():
        return True

    return False
