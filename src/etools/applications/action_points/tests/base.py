from etools.libraries.djangolib.models import GroupWrapper


class ActionPointsTestCaseMixin(object):
    def setUp(self):
        super().setUp()

        # clearing groups cache
        GroupWrapper.invalidate_instances()
