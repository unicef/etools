import datetime

from django.urls import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerOrganization, PartnerType
from etools.applications.partners.tests.factories import AgreementAmendmentFactory, AgreementFactory, PartnerFactory
from etools.libraries.tests.api_checker import ApiCheckerMixin, AssertTimeStampedMixin, ViewSetChecker


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
        self.assertGET(url)

    def test_agreement_list(self):
        url = reverse("partners_api:agreement-list")
        self.assertGET(url)

    def test_agreement_amendment_list(self):
        url = reverse("partners_api:agreement-amendment-list")
        self.assertGET(url)


class TestAPIIntervention(BaseTenantTestCase, metaclass=ViewSetChecker):
    URLS = [
        reverse("partners_api:intervention-list"),
        reverse("partners_api:intervention-detail", args=[101]),
        reverse("partners_api:intervention-indicators"),
        reverse("partners_api:intervention-amendments"),
        reverse("partners_api:intervention-map"),
        reverse("partners_api:intervention-applied-indicators-list"),
    ]


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
            hact_values={'programmatic_visits': {'completed': {'total': 0}}},
            hidden=False,
            reported_cy=10000
        )
        return {
            'partner': partner,
            'partner_not_programmatic_visit_compliant': partner_not_programmatic_visit_compliant,
        }
