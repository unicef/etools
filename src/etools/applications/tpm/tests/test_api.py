from django.urls import reverse

from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.tpm.tests.factories import (
    TPMActivityFactory,
    TPMPartnerFactory,
    TPMUserFactory,
    TPMVisitFactory,
)
from etools.libraries.tests.api_checker import AssertTimeStampedMixin, ViewSetChecker


class TestAPIActivities(AssertTimeStampedMixin, BaseTenantTestCase, metaclass=ViewSetChecker):
    URLS = [
        reverse('tpm:activities-list'),
    ]

    def get_fixtures(cls):
        tpm_partner = TPMPartnerFactory()
        tpm_user = TPMUserFactory(tpm_partner=tpm_partner, email='macioce@unicef.org')
        location = LocationFactory()
        visit = TPMVisitFactory(status='tpm_accepted',
                                tpm_partner=tpm_user.tpmpartners_tpmpartnerstaffmember.tpm_partner,
                                tpm_partner_focal_points=[tpm_user.tpmpartners_tpmpartnerstaffmember],
                                tpm_activities__count=0)

        activity = TPMActivityFactory(tpm_visit=visit, locations=[location])

        return {
            'tpm_partner': tpm_partner,
            'tpm_user': tpm_user,
            'location': location,
            'visit': visit,
            'activity': activity,
        }
