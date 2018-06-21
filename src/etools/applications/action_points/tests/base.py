from etools.applications.EquiTrack.wrappers import GroupWrapper


class ActionPointsTestCaseMixin(object):
    def setUp(self):
        super(ActionPointsTestCaseMixin, self).setUp()

        # clearing groups cache
        GroupWrapper.invalidate_instances()
