from etools.applications.partners.permissions import PMPPermissions


class EFaceFormPermissions(PMPPermissions):
    MODEL_NAME = 'eface.EFaceForm'
    EXTRA_FIELDS = [
        'activities_reporting_expenditures_accepted_by_agency',
        'activities_requested_authorized_amount',
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.user_groups = set(self.user_groups)
        self.user_groups.add('All Users')

        if self.instance.intervention.partner_focal_points.filter(email=self.user.email).exists():
            self.user_groups.add('Partner Focal Point')

        if self.instance.intervention.unicef_focal_points.filter(email=self.user.email).exists():
            self.user_groups.add('UNICEF Focal Point')

        self.condition_map = {}
