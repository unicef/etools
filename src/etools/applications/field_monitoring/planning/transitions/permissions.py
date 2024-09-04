from etools.applications.field_monitoring.groups import FMUser, MonitoringVisitApprover
from etools.applications.tpm.models import PME


def user_is_field_monitor_permission(activity, user):
    return user.groups.filter(name__in=[PME.name, FMUser.name]).exists()


def user_is_visit_lead_permission(activity, user):
    return user == activity.visit_lead


def user_is_pme_or_approver_or_reviewer_permission(activity, user):
    return user.groups.filter(name__in=[PME.name, MonitoringVisitApprover.name]).exists() \
        or user == activity.report_reviewer
