import datetime

from django.db import connection
from django.urls import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import (AgreementFactory, PartnerFactory, InterventionFactory,
                                                          InterventionAmendmentFactory, InterventionResultLinkFactory)
from etools.libraries.utils.test.api_checker import ApiChecker, StandardAPIRecorder


class TestAPIAgreements(ApiChecker, BaseTenantTestCase):
    recorder = StandardAPIRecorder(__file__)

    @recorder.record(AgreementFactory)
    def agreement(self):
        return dict(signed_by_unicef_date=datetime.date.today())

    def setUp(self):
        super().setUp()
        assert self.agreement

    def test_agreement_detail(self):
        url = reverse("partners_api:agreement-detail", args=[self.agreement.pk])
        self.assertAPI(url)

    def test_agreement_list(self):
        url = reverse("partners_api:agreement-list")
        self.assertAPI(url)


class TestAPIIntervention(ApiChecker, BaseTenantTestCase):
    recorder = StandardAPIRecorder(__file__)

    @recorder.record(InterventionFactory)
    def intervention(self):
        return {}

    @recorder.record(InterventionAmendmentFactory)
    def amendment(self):
        return {}

    @recorder.record(InterventionResultLinkFactory)
    def result(self):
        return {}

    def setUp(self):
        connection.set_tenant(self.tenant)
        assert self.intervention
        assert self.result
        assert self.amendment

    def test_intervention_detail(self):
        url = reverse("partners_api:intervention-detail",
                      args=[self.intervention.pk])
        self.assertAPI(url)

    def test_intervention_list(self):
        url = reverse("partners_api:intervention-list")
        self.assertAPI(url)

    def test_intervention_indicator(self):
        url = reverse("partners_api:intervention-indicators")
        self.assertAPI(url)

    def test_intervention_map(self):
        url = reverse("partners_api:intervention-map")
        self.assertAPI(url)

    def test_intervention_amendments(self):
        assert self.result
        url = reverse("partners_api:intervention-amendments")
        self.assertAPI(url)


class TestPartners(ApiChecker, BaseTenantTestCase):
    recorder = StandardAPIRecorder(__file__)

    @recorder.record(PartnerFactory)
    def partner(self):
        return dict(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            hidden=False,
            vendor_number="DDD",
            short_name="Short name",
            modified=datetime.datetime.today()
        )

    def test_detail(self):
        # PartnerOrganizationDetailSerializer
        url = reverse("partners_api:partner-detail", args=[self.partner.pk])
        self.assertAPI(url)

    def test_list(self):
        # PartnerOrganizationDetailSerializer
        assert self.partner
        url = reverse("partners_api:partner-list")
        self.assertAPI(url)
