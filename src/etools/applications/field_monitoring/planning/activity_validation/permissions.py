from etools.applications.field_monitoring.groups import FMUser, MonitoringVisitApprover
from etools.applications.partners.permissions import PMPPermissions
from etools.applications.tpm.models import PME


class ActivityPermissions(PMPPermissions):
    MODEL_NAME = 'field_monitoring_planning.MonitoringActivity'
    EXTRA_FIELDS = [
        'activity_question_set',
        'activity_question_set_review',
        'started_checklist_set',
        'activity_overall_finding',
        'additional_info',
        'report_attachments',
        'action_points',
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.user_groups = set(self.user_groups)
        if {FMUser.name, PME.name}.intersection(self.user_groups):
            self.user_groups.add('Field Monitor')

        if {MonitoringVisitApprover.name, PME.name}.intersection(self.user_groups):
            self.user_groups.add('Approvers')

        self.user_groups.add('All Users')

        def is_visit_lead():
            return self.user == self.instance.visit_lead

        def is_team_member():
            return self.user in self.instance.team_members.all()

        def is_ma_user():
            return is_visit_lead() or is_team_member()

        monitor_types = self.instance.MONITOR_TYPE_CHOICES

        self.condition_map = {
            'is_ma_related_user': is_ma_user(),
            'is_visit_lead': is_visit_lead(),
            'tpm_visit': self.instance.monitor_type == monitor_types.tpm,
            'staff_visit': self.instance.monitor_type == monitor_types.staff,
            'staff_visit+is_visit_lead': self.instance.monitor_type == monitor_types.staff and is_visit_lead(),
            'tpm_visit+tpm_ma_related': self.instance.monitor_type == monitor_types.tpm and is_ma_user(),
        }
