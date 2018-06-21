
from django.core.management import call_command

from etools.applications.tpm.tests.factories import UserFactory, TPMPartnerFactory
from etools.applications.utils.groups.wrappers import GroupWrapper


class TPMTestCaseMixin(object):
    @classmethod
    def setUpTestData(cls):
        call_command('update_tpm_permissions', verbosity=0)
        call_command('update_notifications')

        # clearing groups cache
        GroupWrapper.invalidate_instances()

        cls.pme_user = UserFactory(pme=True)
        cls.unicef_user = UserFactory(unicef_user=True)

        cls.tpm_partner = TPMPartnerFactory()
        cls.tpm_user = UserFactory(tpm=True, tpm_partner=cls.tpm_partner)
