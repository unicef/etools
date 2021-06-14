from etools.applications.field_monitoring.groups import FMUser
from etools.applications.tpm.models import PME


def user_is_pme_permission(activity, user):
    return PME.as_group() in user.groups.all()


def user_is_field_monitor_permission(activity, user):
    if {FMUser.as_group(), PME.as_group()}.intersection(user.groups.all()):
        return True
    return False


def user_is_visit_lead_permission(activity, user):
    return user == activity.visit_lead
