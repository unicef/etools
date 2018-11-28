from etools.libraries.djangolib.models import GroupWrapper


class ActionPointsTestCaseMixin(object):
    def setUp(self):
        super(ActionPointsTestCaseMixin, self).setUp()

        # clearing groups cache
        GroupWrapper.invalidate_instances()
