from etools.applications.partners.permissions import PMPPermissions


class EFaceFormPermissions(PMPPermissions):
    MODEL_NAME = 'eface.EFaceForm'
    EXTRA_FIELDS = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.user_groups = set(self.user_groups)
        self.user_groups.add('All Users')

        if self.instance.intervention.partner_focal_points.filter(email=self.user.email).exists():
            self.user_groups.add('Partner Focal Point')

        def is_programme_officer():
            return self.instance.intervention.unicef_focal_points.filter(email=self.user.email).exists()

        self.condition_map = {
            'is_programme_officer': is_programme_officer(),
        }
