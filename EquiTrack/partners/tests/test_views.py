__author__ = 'unicef-leb-inn'

import json
import datetime

from rest_framework import status

from EquiTrack.factories import (
    PartnershipFactory,
    PartnerFactory,
    UserFactory,
    ResultFactory,
    ResultStructureFactory,
    LocationFactory,
    AgreementFactory,
    OfficeFactory,
    PartnerStaffFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase
from reports.models import ResultType, Sector
from funds.models import Grant, Donor
from supplies.models import SupplyItem
from partners.models import (
    PCA,
    Agreement,
    PartnerOrganization,
    ResultChain,
    PCASector,
    PartnershipBudget,
    PCAGrant,
    AmendmentLog,
    GwPCALocation,
    SupplyPlan,
    DistributionPlan,
)


class TestPartnershipViews(APITenantTestCase):
    fixtures = ['initial_data.json']
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory()
        agreement = AgreementFactory(partner=self.partner)
        self.intervention = PartnershipFactory(partner=self.partner, agreement=agreement)
        assert self.partner == self.intervention.partner

        self.result_type = ResultType.objects.get(id=1)
        self.result = ResultFactory(result_type=self.result_type, result_structure=ResultStructureFactory())
        self.resultchain = ResultChain.objects.create(
            result=self.result,
            result_type=self.result_type,
            partnership=self.intervention,
        )
        self.pcasector = PCASector.objects.create(
            pca=self.intervention,
            sector=Sector.objects.create(name="Sector 1")
        )
        self.partnership_budget = PartnershipBudget.objects.create(
            partnership=self.intervention,
            unicef_cash=100
        )
        self.grant = Grant.objects.create(
            donor=Donor.objects.create(
                name="Donor 1"
            ),
            name="Grant 1"
        )
        self.pcagrant = PCAGrant.objects.create(
            partnership=self.intervention,
            grant=self.grant,
            funds=100
        )
        self.amendment = AmendmentLog.objects.create(
            partnership=self.intervention,
            type="Cost",
        )
        self.location = GwPCALocation.objects.create(
            pca=self.intervention,
            location=LocationFactory()
        )


    def test_api_partners_list(self):
        response = self.forced_auth_req('get', '/api/partners/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Partner", response.data[0]["name"])

    def test_api_agreements_create(self):

        data = {
            "agreement_type": "PCA",
            "partner": self.intervention.partner.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/partners/'+str(self.intervention.partner.id)+'/agreements/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_api_agreements_list(self):

        response = self.forced_auth_req('get', '/api/partners/'+str(self.intervention.partner.id)+'/agreements/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("PCA", response.data[0]["agreement_type"])

    def test_api_interventions_list(self):

        response = self.forced_auth_req('get', '/api/partners/'+str(self.intervention.partner.id)+'/interventions/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("galaxy", response.data[0]["pca_title"])
        self.assertIn("galaxy", response.data[0]["title"])
        self.assertIn("in_process", response.data[0]["status"])
        self.assertIn("PD", response.data[0]["partnership_type"])

    def test_api_agreement_interventions_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'agreements',
                                            str(self.intervention.agreement.id),
                                            'interventions/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("galaxy", response.data[0]["title"])
        self.assertIn("in_process", response.data[0]["status"])

    def test_api_staffmembers_list(self):
        response = self.forced_auth_req('get',
                                        '/'.join(['/api/partners', str(self.partner.id), 'staff-members/']),
                                        user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Jedi Master", response.data[0]["title"])
        self.assertIn("Mace", response.data[0]["first_name"])
        self.assertIn("Windu", response.data[0]["last_name"])
        self.assertEqual(True, response.data[0]["active"])


    # TODO: removed intervention results until after R3
    # def test_api_interventions_results_list(self):
    #
    #     response = self.forced_auth_req('get',
    #                                     '/'.join([
    #                                         '/api/partners',
    #                                         str(self.intervention.partner.id),
    #                                         'interventions',
    #                                         str(self.intervention.id),
    #                                         'results/'
    #                                     ]), user=self.unicef_staff)
    #
    #     self.assertEquals(response.status_code, status.HTTP_200_OK)
    #     self.assertEquals(len(response.data), 1)
    #     self.assertIn("Result", response.data[0]["result"]["name"])

    def test_api_interventions_sectors_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'sectors/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Sector", response.data[0]["sector_name"])

    def test_api_interventions_budgets_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'budgets/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["unicef_cash"], 100)
        self.assertEquals(response.data[0]["total"], 100)

    def test_api_interventions_files_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'files/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_interventions_grants_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'grants/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["grant"], self.grant.id)
        self.assertEquals(response.data[0]["funds"], 100)

    def test_api_interventions_amendments_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'amendments/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["type"], "Cost")

    def test_api_interventions_locations_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'locations/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Location", response.data[0]["location_name"])


class TestPartnerOrganizationViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory()

    def test_api_partners_list(self):
        response = self.forced_auth_req('get', '/api/partners/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)

    def test_api_partners_create(self):
        data = {
            "name": "PO 1",
            "partner_type": "Government",
            "vendor_number": "AAA",
        }
        response = self.forced_auth_req(
            'post',
            '/api/partners/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)


class TestPCAViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory()
        self.agreement = AgreementFactory()
        self.pca = PCA.objects.create(
                                partner=self.partner,
                                agreement=self.agreement,
                                title="PCA 1",
                                initiation_date=datetime.date.today(),
                                status=PCA.DRAFT,
                            )

    def test_pca_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)

    def test_pca_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/{}/'.format(self.pca.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["id"], self.pca.id)

    def test_pca_create_errors(self):
        today = datetime.date.today()
        data = {
            "partner": self.partner.id,
            "title": "PCA 2",
            "agreement": self.agreement.id,
            "initiation_date": datetime.date.today(),
            "status": PCA.ACTIVE,
            "signed_by_unicef_date": datetime.date(today.year-1, 1, 1),
            "signed_by_partner_date": datetime.date(today.year-2, 1, 1),
            "budget_log": [],
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=data,
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["partnership_type"], ["This field is required.","This field must be PD or SHPD in case of agreement is PCA."])
        self.assertEquals(response.data["office"], ["This field is required."])
        self.assertEquals(response.data["programme_focal_points"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])
        self.assertEquals(response.data["unicef_managers"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])
        self.assertEquals(response.data["partner_focal_point"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])
        self.assertEquals(response.data["start_date"], ["This field is required."])
        self.assertEquals(response.data["end_date"], ["This field is required."])
        self.assertEquals(response.data["signed_by_unicef_date"], ["signed_by_unicef_date and unicef_manager must be provided."])
        self.assertEquals(response.data["signed_by_partner_date"], ["signed_by_partner_date and partner_manager must be provided."])
        self.assertEquals(response.data["partner_manager"], ["partner_manager and signed_by_partner_date must be provided."])
        self.assertEquals(response.data["unicef_manager"], ["unicef_manager and signed_by_unicef_date must be provided."])
        self.assertEquals(response.data["population_focus"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])

    def test_pca_create_update(self):
        today = datetime.date.today()
        partner_staff = PartnerStaffFactory(partner=self.partner)
        supply_item = SupplyItem.objects.create(name="Item1")
        sector = Sector.objects.create(name="Sector1")
        pcasector = {
            "sector": sector.id,
        }
        supply_plan = {
            "item": supply_item.id,
            "quantity": 5,
        }
        budget_log = {
            "year": today.year,
            "partner_contribution": 1000,
            "unicef_cash": 1000,
        }
        distribution_plan = {
            "item": supply_item.id,
            "site": LocationFactory().id,
            "quantity": 5,
        }
        amendment_log = {
            "amended_at": today,
            "type": "Change in Programme Result",
        }
        unicef_manager = UserFactory()
        result_structure = ResultStructureFactory()
        office = OfficeFactory()
        location = LocationFactory()
        gwpcalocation = {
            "location": location.id,
        }
        visit = {
            "year": 2016,
            "programmatic": 1,
            "spot_checks": 1,
            "audit": 1,
        }
        data = {
            "partner": self.partner.id,
            "title": "PCA 2",
            "agreement": self.agreement.id,
            "initiation_date": datetime.date.today(),
            "status": PCA.ACTIVE,
            "partnership_type": PCA.PD,
            "result_structure": result_structure.id,
            "office": [office.id],
            "programme_focal_points": [UserFactory().id],
            "unicef_managers": [unicef_manager.id],
            "partner_focal_point": [partner_staff.id],
            "partner_manager": partner_staff.id,
            "unicef_manager": self.unicef_staff.id,
            "start_date": today,
            "end_date": datetime.date(today.year+1, 1, 1),
            "signed_by_unicef_date": datetime.date(today.year-1, 1, 1),
            "signed_by_partner_date": datetime.date(today.year-2, 1, 1),
            "population_focus": "focus1",
            "pcasectors": [pcasector],
            "locations": [gwpcalocation],
            "budget_log": [budget_log],
            "supply_plans": [supply_plan],
            "distribution_plans": [distribution_plan],
            "fr_numbers": ["Grant"],
            "amendments_log": [amendment_log],
            "visits": [visit],
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=data,
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        # Test updates
        data = response.data
        data.update(budget_log=[budget_log, budget_log])
        data.update(supply_plans=[supply_plan, supply_plan])
        data.update(distribution_plans=[distribution_plan, distribution_plan])
        data.update(amendments_log=[amendment_log, amendment_log])
        data.update(pcasectors=[pcasector, pcasector])
        data.update(locations=[gwpcalocation, gwpcalocation])
        data.update(fr_numbers=["Grant", "WBS"])
        data.update(visits=[visit, visit])

        response = self.forced_auth_req(
            'put',
            '/api/v2/interventions/{}/'.format(data["id"]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data["budget_log"]), 2)
        self.assertEquals(len(response.data["supply_plans"]), 2)
        self.assertEquals(len(response.data["distribution_plans"]), 2)
        self.assertEquals(len(response.data["amendments_log"]), 2)
        self.assertEquals(len(response.data["pcasectors"]), 2)
        self.assertEquals(len(response.data["locations"]), 2)
        self.assertEquals(len(response.data["fr_numbers"]), 2)
        self.assertEquals(len(response.data["visits"]), 2)

        # Test filter
        params = {
            "partnership_type": PCA.PD,
            "sector": sector.id,
            "location": location.id,
            "status": PCA.ACTIVE,
            "unicef_managers": unicef_manager.id,
            "start_date": datetime.date(today.year-1, 1, 1),
            "end_date": datetime.date(today.year+1, 1, 1),
            "office": office.id,
            "search": "PCA 2",
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data[0]["id"], data["id"])
