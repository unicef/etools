__author__ = 'unicef-leb-inn'

import json
import datetime
from datetime import date

from rest_framework import status

from EquiTrack.factories import (
    PartnershipFactory,
    PartnerFactory,
    UserFactory,
    ResultFactory,
    ResultStructureFactory,
    LocationFactory,
    AgreementFactory,
    PartnerStaffFactory,
    CountryProgrammeFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase
from reports.models import ResultType, Sector
from funds.models import Grant, Donor
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
)


class TestPartnershipViews(APITenantTestCase):
    fixtures = ['initial_data.json']
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory()
        agreement = AgreementFactory(partner=self.partner, signed_by_unicef_date=datetime.date.today())
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
            "status": "active"
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

    def test_api_interventions_results_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'results/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Result", response.data[0]["result"]["name"])

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


class TestAgreementAPIView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(partner_type="Civil Society Organization")
        self.partner_staff = PartnerStaffFactory(partner=self.partner)
        self.partner_staff_user = UserFactory(is_staff=True)
        self.partner_staff_user.profile.partner_staff_member = self.partner_staff.id
        self.partner_staff_user.save()
        self.agreement = AgreementFactory(partner=self.partner, signed_by_unicef_date=datetime.date.today())
        self.agreement2 = AgreementFactory(
                                partner=self.partner,
                                agreement_type="MOU",
                                status="draft"
                            )
        self.intervention = PartnershipFactory(partner=self.partner, agreement=self.agreement)
        self.result_type = ResultType.objects.get(id=1)
        today = datetime.date.today()
        self.country_programme = CountryProgrammeFactory(
                                        wbs='/A0/',
                                        from_date=date(today.year-1, 1, 1),
                                        to_date=date(today.year+1, 1, 1))
        self.result_structure=ResultStructureFactory(country_programme=self.country_programme)
        self.result = ResultFactory(result_type=self.result_type, result_structure=self.result_structure)
        self.resultchain = ResultChain.objects.create(
            result=self.result,
            result_type=self.result_type,
            partnership=self.intervention,
        )

    def test_partner_agreements_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/agreements/'.format(self.partner.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])
        self.assertEquals(response.data[0]["agreement_type"], Agreement.AGREEMENT_TYPES[2][0])

    def test_partner_agreements_create(self):
        data = {
            "agreement_type":"PCA",
            "partner": self.partner.id,
            "status": "draft"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/partners/{}/agreements/'.format(self.partner.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_partner_agreements_update(self):
        data = {
            "status":"active",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/agreements/{}/'.format(self.partner.id, self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "active")

    def test_partner_agreements_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/agreements/{}/'.format(self.partner.id, self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["agreement_type"], Agreement.AGREEMENT_TYPES[0][0])

    def test_agreements_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])
        self.assertEquals(response.data[0]["agreement_type"], Agreement.AGREEMENT_TYPES[0][0])

    def test_agreements_create(self):
        data = {
            "agreement_type":"PCA",
            "partner": self.partner.id,
            "status": "draft"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_agreements_update(self):
        data = {
            "status":"active",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "active")

    def test_agreements_update_no_perm(self):
        data = {
            "status":"active",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agreements_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["agreement_type"], Agreement.AGREEMENT_TYPES[0][0])

    def test_agreements_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["reference_number"], "/PCA{}01".format(datetime.date.today().year))

    def test_agreements_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partner_staff_user
        )

        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agreements_delete_no_perm(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agreements_create_cp_todate(self):
        data = {
            "agreement_type":"PCA",
            "partner": self.partner.id,
            "status": "draft"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data["end"], str(self.country_programme.to_date))

    def test_agreements_list_filter_type(self):
        params = {"agreement_type": "PCA"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["id"], self.agreement.id)
        self.assertEquals(response.data[0]["agreement_type"], "PCA")

    def test_agreements_list_filter_status(self):
        params = {"status": "active"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["id"], self.agreement.id)
        self.assertEquals(response.data[0]["status"], "active")

    def test_agreements_list_filter_partner_name(self):
        params = {"partner_name": self.partner.name}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 2)
        self.assertEquals(self.partner.name, response.data[0]["partner_name"])

    def test_agreements_list_filter_search(self):
        params = {"search": "Partner"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])

    def test_agreements_list_filter_search_refno(self):
        params = {"search": datetime.date.today().year}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["reference_number"], "/PCA{}01".format(datetime.date.today().year))

    def test_api_agreement_interventions_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/v2/partners',
                                            str(self.intervention.partner.id),
                                            'agreements',
                                            str(self.intervention.agreement.id),
                                            'interventions/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("galaxy", response.data[0]["pca_title"])

    def test_agreements_update_validation_signed_by(self):
        data = {
            "end": datetime.date.today(),
            "signed_by_partner_date": datetime.date.today(),
            "signed_by_unicef_date": datetime.date.today(),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["signed_by_partner_date"], ["signed_by_partner_date and partner_manager are both must be provided."])
        self.assertEquals(response.data["partner_manager"], ["partner_manager and signed_by_partner_date are both must be provided."])
        self.assertEquals(response.data["signed_by_unicef_date"], ["signed_by_unicef_date and signed_by are both must be provided."])
        self.assertEquals(response.data["signed_by"], ["signed_by and signed_by_unicef_date are both must be provided."])
        self.assertEquals(response.data["start"], ["Start date must be provided along with end date."])

    def test_agreements_update_validation_signed_date(self):
        data = {
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["signed_by_partner_date"], ["signed_by_partner_date and partner_manager are both must be provided."])
        self.assertEquals(response.data["partner_manager"], ["partner_manager and signed_by_partner_date are both must be provided."])
        self.assertEquals(response.data["signed_by_unicef_date"], ["signed_by_unicef_date and signed_by are both must be provided."])
        self.assertEquals(response.data["signed_by"], ["signed_by and signed_by_unicef_date are both must be provided."])

    def test_agreements_update_validation_end_date_pca(self):
        data = {
            "start": datetime.date.today(),
            "end": datetime.date.today(),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # self.assertEquals(response.data["end"], str(self.country_programme.to_date))

    def test_agreements_update_start_set_to_max_signed(self):
        today = datetime.date.today()
        data = {
            "start": date(today.year, 1, 1),
            "end": date(today.year, 6, 1),
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
            "signed_by_partner_date": date(today.year, 2, 1),
            "signed_by_unicef_date": date(today.year, 3, 1),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["start"], response.data["signed_by_unicef_date"])

    def test_agreements_create_PCA_must_be_CSO(self):
        self.partner.partner_type = "Government"
        self.partner.save()
        data = {
            "agreement_type":"PCA",
            "partner": self.partner.id,
            "status": "draft"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["partner"], ["Partner type must be CSO for PCA or SSFA agreement types."])

    def test_agreements_update_set_to_active_on_save(self):
        today = datetime.date.today()
        data = {
            "start": date(today.year, 1, 1),
            "end": date(today.year, 6, 1),
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
            "signed_by_partner_date": date(today.year, 2, 1),
            "signed_by_unicef_date": date(today.year, 3, 1),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], Agreement.ACTIVE)

    def test_partner_agreements_update_suspend(self):
        data = {
            "status":"suspended",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/agreements/{}/'.format(self.partner.id, self.agreement.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "suspended")
        self.assertEquals(PCA.objects.get(id=self.intervention.id).status, "suspended")
