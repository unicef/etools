from etools.applications.field_monitoring.groups import FMUser, PME
from etools.applications.partners.permissions import PMPPermissions


class ActivityPermissions(PMPPermissions):

    MODEL_NAME = 'field_monitoring_planning.MonitoringActivity'
    EXTRA_FIELDS = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.user_groups = set(self.user_groups)
        if {FMUser.name, PME.name}.intersection(self.user_groups):
            self.user_groups.add('Field Monitor')

        # def user_added_amendment(instance):
        #     return instance.in_amendment is True

        self.condition_map = {
            'is_tpm': self.instance.activity_type == 'tpm',
            # 'condition1': self.user in self.instance.unicef_focal_points.all(),
            # 'not_in_amendment_mode': not user_added_amendment(self.instance),
            # 'not_ended': self.instance.end >= datetime.datetime.now().date() if self.instance.end else False
        }
