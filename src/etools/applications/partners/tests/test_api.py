import datetime

from django.urls import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import (AgreementFactory, PartnerFactory, InterventionFactory,
                                                          InterventionAmendmentFactory, InterventionResultLinkFactory)
from etools.libraries.utils.test.api_checker import ApiChecker, ViewSetChecker, AssertTimeStampedMixin


class TestAPIAgreements(ApiChecker, AssertTimeStampedMixin, BaseTenantTestCase):

    def get_fixtures(self):
        return {'agreement': AgreementFactory(signed_by_unicef_date=datetime.date.today())}

    def test_agreement_detail(self):
        url = reverse("partners_api:agreement-detail", args=[self.get_fixture('agreement').pk])
        self.assertAPI(url)

    def test_agreement_list(self):
        url = reverse("partners_api:agreement-list")
        self.assertAPI(url)


class TestAPIIntervention(BaseTenantTestCase, metaclass=ViewSetChecker):

    def get_fixtures(cls):
        return {'intervention': InterventionFactory(id=101),
                'amendment': InterventionAmendmentFactory(),
                'result': InterventionResultLinkFactory(),
                }

    @classmethod
    def get_urls(self):
        return [
            reverse("partners_api:intervention-list"),
            reverse("partners_api:intervention-detail", args=[101]),
            reverse("partners_api:intervention-indicators"),
            reverse("partners_api:intervention-amendments"),
            reverse("partners_api:intervention-map"),
        ]


class TestPartners(ApiChecker, BaseTenantTestCase):

    def get_fixtures(self):
        return {'partner': PartnerFactory(hidden=False,
                                          partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
                                          cso_type="International",
                                          vendor_number="DDD",
                                          short_name="Short name",
                                          modified=datetime.datetime.today()
                                          )}

    def test_detail(self):
        url = reverse("partners_api:partner-detail",
                      args=[self.get_fixture('partner').pk])
        self.assertAPI(url)

    def test_list(self):
        url = reverse("partners_api:partner-list")
        self.assertAPI(url)
