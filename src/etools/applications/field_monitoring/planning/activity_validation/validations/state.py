from django.utils.translation import gettext_lazy as _

from etools_validator.exceptions import StateValidationError

from etools.applications.field_monitoring.data_collection.models import ActivityQuestionOverallFinding
from etools.applications.field_monitoring.planning.models import MonitoringActivity


def tpm_partner_is_assigned_for_tpm_activity(i):
    if i.monitor_type == MonitoringActivity.MONITOR_TYPE_CHOICES.tpm and not i.tpm_partner:
        raise StateValidationError([_('Partner is not defined for TPM activity')])
    return True


def at_least_one_item_added(i):
    if not any([i.partners.exists(), i.interventions.exists(), i.cp_outputs.exists()]):
        raise StateValidationError([_('At least one Partner, CP Output, or PD/SPD should be added')])
    return True


def reject_reason_provided(i, old_status):
    if old_status == MonitoringActivity.STATUSES.assigned and not i.reject_reason:
        raise StateValidationError([_('Rejection reason should be provided.')])
    return True


def cancel_reason_provided(i):
    if not i.cancel_reason:
        raise StateValidationError([_('Cancellation reason should be provided.')])
    return True


def report_reject_reason_provided(i, old_status):
    if old_status == MonitoringActivity.STATUSES.submitted and not i.report_reject_reason:
        raise StateValidationError([_('Report reject reason should be provided.')])
    return True


def activity_questions_required(i):
    if not i.questions.filter(is_enabled=True).exists():
        raise StateValidationError([_('At least one question should be enabled.')])
    return True


def started_checklists_required(i):
    if not i.checklists.exists():
        raise StateValidationError([_('At least one checklist should be completed.')])
    return True


def activity_overall_findings_required(i):
    has_narrative_completed = i.overall_findings.exclude(narrative_finding='').exists()
    has_value_completed = ActivityQuestionOverallFinding.objects.filter(
        activity_question__monitoring_activity=i,
        value__isnull=False
    ).exists()

    if not (has_narrative_completed or has_value_completed):
        raise StateValidationError([_('At least one summary finding should be completed.')])
    return True
