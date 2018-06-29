import datetime

from django.urls import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerType, PartnerOrganization
from etools.applications.partners.tests.factories import (AgreementFactory, AgreementAmendmentFactory, PartnerFactory, InterventionFactory,
                                                          InterventionAmendmentFactory, InterventionResultLinkFactory)
from etools.libraries.utils.test.api_checker import ApiCheckerMixin, ViewSetChecker, AssertTimeStampedMixin


class TestAPIAgreements(ApiCheckerMixin, AssertTimeStampedMixin, BaseTenantTestCase):

    def get_fixtures(self):
        agreement = AgreementFactory(signed_by_unicef_date=datetime.date.today())
        agreement_amendment = AgreementAmendmentFactory(agreement=agreement)
        return {
            'agreement': agreement,
            'agreement_amendment': agreement_amendment,
        }

    def test_agreement_detail(self):
        url = reverse("partners_api:agreement-detail", args=[self.get_fixture('agreement').pk])
        self.assertAPI(url)

    def test_agreement_list(self):
        url = reverse("partners_api:agreement-list")
        self.assertAPI(url)

    def test_agreement_amendement_list(self):
        url = reverse("partners_api:agreement-amendment-list")
        self.assertAPI(url)


class TestAPIIntervention(BaseTenantTestCase, metaclass=ViewSetChecker):
    URLS = [
        reverse("partners_api:intervention-list"),
        reverse("partners_api:intervention-detail", args=[101]),
        reverse("partners_api:intervention-indicators"),
        reverse("partners_api:intervention-amendments"),
        reverse("partners_api:intervention-map"),
    ]

    def get_fixtures(cls):
        return {'intervention': InterventionFactory(id=101),
                'amendment': InterventionAmendmentFactory(),
                'result': InterventionResultLinkFactory(),
                }


class TestPartners(BaseTenantTestCase, metaclass=ViewSetChecker):
    URLS = [
        reverse("partners_api:partner-list"),
        reverse("partners_api:partner-detail", args=[101]),
        reverse("partners_api:partner-list-not-programmatic-visit"),
    ]

    def get_fixtures(self):
        partner = PartnerFactory(
            id=101,
            hidden=False,
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            vendor_number="DDD",
            short_name="Short name",
            modified=datetime.datetime.today()
        )
        partner_not_programmatic_visit_compliant = PartnerFactory(
            net_ct_cy=PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL + 1,
            hact_values={'programmatic_visits': {'completed': {'total': 0}}}
        )
        return {
            'partner': partner,
            'partner_not_programmatic_visit_compliant': partner_not_programmatic_visit_compliant,
        }
