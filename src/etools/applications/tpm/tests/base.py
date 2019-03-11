from django.core.management import call_command

from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMUserFactory
from etools.applications.users.tests.factories import UserFactory, PMEUserFactory
from etools.libraries.djangolib.models import GroupWrapper


class TPMTestCaseMixin(object):
    @classmethod
    def setUpTestData(cls):
        call_command('update_tpm_permissions', verbosity=0)
        call_command('update_notifications')

        # clearing groups cache
        GroupWrapper.invalidate_instances()

        cls.pme_user = PMEUserFactory()
        cls.unicef_user = UserFactory()

        cls.tpm_partner = TPMPartnerFactory()
        cls.tpm_user = TPMUserFactory(tpm_partner=cls.tpm_partner)
