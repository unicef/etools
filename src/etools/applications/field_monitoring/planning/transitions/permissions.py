from etools.applications.field_monitoring.groups import FMUser
from etools.applications.tpm.models import PME


def user_is_pme_permission(activity, user):
    return user in activity.country_pmes


def user_is_field_monitor_permission(activity, user):
    return user.groups.filter(name__in=[PME.name, FMUser.name]).exists()


def user_is_visit_lead_permission(activity, user):
    return user == activity.visit_lead
