from etools.applications.field_monitoring.groups import FMUser, PME
from etools.applications.partners.permissions import PMPPermissions


class ActivityPermissions(PMPPermissions):
    MODEL_NAME = 'field_monitoring_planning.MonitoringActivity'
    EXTRA_FIELDS = [
        'activity_question_set',
        'started_checklist_set',
        'activity_overall_finding',
        'activity_question_overall_finding',
        'related_documents',
        'action_points',
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.user_groups = set(self.user_groups)
        if {FMUser.name, PME.name}.intersection(self.user_groups):
            self.user_groups.add('Field Monitor')

        self.user_groups.add('All Users')

        def is_ma_user():
            return self.user in self.instance.team_members.all() or self.user == self.instance.person_responsible

        self.condition_map = {
            'is_ma_related_user': is_ma_user(),
            'tpm_visit+tpm_ma_related': self.instance.activity_type == 'tpm' and is_ma_user()
        }
