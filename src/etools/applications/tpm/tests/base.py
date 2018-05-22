
from django.core.management import call_command

from etools.applications.utils.groups.wrappers import GroupWrapper


class TPMTestCaseMixin(object):
    @classmethod
    def setUpTestData(cls):
        call_command('update_tpm_permissions', verbosity=0)

    def setUp(self):
        super(TPMTestCaseMixin, self).setUp()

        # clearing groups cache
        GroupWrapper.invalidate_instances()
