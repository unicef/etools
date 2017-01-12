__author__ = 'unicef-leb-inn'

from unittest import skip
import json
import datetime
from datetime import date

from rest_framework import status

from actstream import action
from actstream.models import model_stream

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
    CountryProgrammeFactory,
    GroupFactory,
    InterventionFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase
from reports.models import ResultType, Sector
from funds.models import Grant, Donor
from supplies.models import SupplyItem
from partners.models import (
    PCA,
    Agreement,
    PartnerOrganization,
    PartnerType,
    PCASector,
    PartnershipBudget,
    PCAGrant,
    AmendmentLog,
    GwPCALocation,
    SupplyPlan,
    DistributionPlan,
    Intervention,
    InterventionSectorLocationLink,
    InterventionBudget,
    InterventionAmendment,
)


class TestPartnerOrganizationViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(
                            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
                            cso_type="International",
                            hidden=False,
                            vendor_number="DDD",
                            short_name="Short name",
                        )

    def test_api_partners_list_restricted(self):
        response = self.forced_auth_req('get', '/api/v2/partners/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("vendor_number", response.data[0].keys())
        self.assertNotIn("address", response.data[0].keys())

    def test_api_partners_create(self):
        data = {
            "name": "PO 1",
            "partner_type": "Government",
            "vendor_number": "AAA",
            "staff_members": [],
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_api_partners_create_with_members(self):
        staff_members = [{
                "title": "Some title",
                "first_name": "John",
                "last_name": "Doe",
                "email": "a@a.com",
                "active": True,
            }]
        data = {
            "name": "PO 1",
            "partner_type": "Government",
            "vendor_number": "AAA",
            "staff_members": staff_members,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_api_partners_update_with_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data["staff_members"]), 1)
        self.assertEquals(response.data["staff_members"][0]["first_name"], "Mace")

        staff_members = [{
                "title": "Some title",
                "first_name": "John",
                "last_name": "Doe",
                "email": "a@a.com",
                "active": True,
            }]
        data = {
            "name": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "staff_members": staff_members,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data["staff_members"]), 2)

    def test_api_partners_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn("vendor_number", response.data.keys())
        self.assertIn("address", response.data.keys())
        self.assertIn("Partner", response.data["name"])

    def test_api_partners_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn("staff_members", response.data.keys())
        self.assertEquals(len(response.data["staff_members"]), 1)

    def test_api_partners_update(self):
        data = {
            "name": "Updated name",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn("Updated", response.data["name"])

    def test_api_partners_filter_partner_type(self):
        # make some other type to filter against
        PartnerFactory(partner_type=PartnerType.GOVERNMENT)
        params = {"partner_type": PartnerType.CIVIL_SOCIETY_ORGANIZATION}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["id"], self.partner.id)
        self.assertEquals(response.data[0]["partner_type"], PartnerType.CIVIL_SOCIETY_ORGANIZATION)

    def test_api_partners_filter_cso_type(self):
        # make some other type to filter against
        PartnerFactory(cso_type="National")
        params = {"cso_type": "International"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["id"], self.partner.id)

    def test_api_partners_filter_hidden(self):
        # make some other type to filter against
        PartnerFactory(hidden=True)
        params = {"hidden": False}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["id"], self.partner.id)

    def test_api_partners_filter_multiple(self):
        # make some other type to filter against
        PartnerFactory(cso_type="National")
        params = {
            "cso_type": "National",
            "partner_type": PartnerType.CIVIL_SOCIETY_ORGANIZATION,
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 0)

    def test_api_partners_search_name(self):
        # make some other type to filter against
        PartnerFactory(name="Somethingelse")
        params = {"search": "Partner"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["id"], self.partner.id)

    def test_api_partners_short_name(self):
        # make some other type to filter against
        PartnerFactory(short_name="foo")
        params = {"search": "Short"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["id"], self.partner.id)


class TestPartnershipViews(APITenantTestCase):
    fixtures = ['initial_data.json']
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory()
        agreement = AgreementFactory(partner=self.partner, signed_by_unicef_date=datetime.date.today())
        self.intervention = InterventionFactory(agreement=agreement)

        self.result_type = ResultType.objects.get(id=1)
        self.result = ResultFactory(result_type=self.result_type, result_structure=ResultStructureFactory())
        self.pcasector = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 1")
        )
        self.partnership_budget = InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.amendment = InterventionAmendment.objects.create(
            intervention=self.intervention,
            type="Change in Programme Result",
        )
        self.location = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 2")
        )


    def test_api_partners_list(self):
        response = self.forced_auth_req('get', '/api/v2/partners/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Partner", response.data[0]["name"])

    @skip("Fix this")
    def test_api_agreements_create(self):

        data = {
            "agreement_type": "PCA",
            "partner": self.partner.id,
            "status": "active"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/partners/'+str(self.partner.id)+'/agreements/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        # Check for activity action created
        self.assertEquals(model_stream(Agreement).count(), 1)

    def test_api_agreements_list(self):

        response = self.forced_auth_req('get', '/api/partners/'+str(self.partner.id)+'/agreements/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("PCA", response.data[0]["agreement_type"])

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

    @skip("skip v1 for now")
    def test_api_interventions_sectors_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'sectors/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Sector", response.data[0]["sector_name"])

    @skip("skip v1 for now")
    def test_api_interventions_budgets_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.partner.id),
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
                                            str(self.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'files/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    @skip("skip v1 for now")
    def test_api_interventions_amendments_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'amendments/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["type"], "Cost")

    @skip("skip v1 for now")
    def test_api_interventions_locations_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'locations/'
                                        ]), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertIn("Location", response.data[0]["location_name"])


class TestAgreementAPIView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(partner_type="Civil Society Organization")
        self.partner_staff = PartnerStaffFactory(partner=self.partner)
        self.partner_staff2 = PartnerStaffFactory(partner=self.partner)

        self.partner_staff_user = UserFactory(is_staff=True)
        self.partner_staff_user.profile.partner_staff_member = self.partner_staff.id
        self.partner_staff_user.save()

        self.partnership_manager_user = UserFactory(is_staff=True)
        self.partnership_manager_user.groups.add(GroupFactory())
        self.partnership_manager_user.profile.partner_staff_member = self.partner_staff.id
        self.partnership_manager_user.save()

        self.agreement = AgreementFactory(
                            partner=self.partner,
                            partner_manager=self.partner_staff,
                            signed_by_unicef_date=datetime.date.today()
                        )
        self.agreement.authorized_officers.add(self.partner_staff)
        self.agreement.save()
        self.agreement2 = AgreementFactory(
                                partner=self.partner,
                                agreement_type="MOU",
                                status="draft"
                            )
        self.intervention = InterventionFactory(
                                agreement=self.agreement,
                                document_type=Intervention.PD)
        today = datetime.date.today()
        self.country_programme = CountryProgrammeFactory(
                                        wbs='/A0/',
                                        from_date=date(today.year-1, 1, 1),
                                        to_date=date(today.year+1, 1, 1))

    def test_agreements_create(self):
        data = {
            "agreement_type":"PCA",
            "partner": self.partner.id,
            "status": "draft"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_agreements_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])

    def test_agreements_update(self):
        data = {
            "status":"active",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "active")

    def test_agreements_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["agreement_number"], self.agreement.agreement_number)

    def test_agreements_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["authorized_officers"][0]["first_name"], self.partner_staff.first_name)

    def test_agreements_update_partner_staff(self):
        data = {
            "authorized_officers": [
                self.partner_staff.id,
                self.partner_staff2.id
            ],
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["authorized_officers"], [self.partner_staff.id, self.partner_staff2.id])

    def test_agreements_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user
        )

        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agreements_create_cp_todate(self):
        data = {
            "agreement_type":"PCA",
            "partner": self.partner.id,
            "status": "draft"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data["end"], str(self.country_programme.to_date))

    def test_agreements_list_filter_type(self):
        params = {"agreement_type": "PCA"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/'.format(self.partner.id),
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
            '/api/v2/agreements/'.format(self.partner.id),
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
            '/api/v2/agreements/'.format(self.partner.id),
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
            '/api/v2/agreements/'.format(self.partner.id),
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
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["agreement_number"], self.agreement.agreement_number)

    def test_agreements_update_validation_signed_by(self):
        data = {
            "end": datetime.date.today(),
            "signed_by_partner_date": datetime.date.today(),
            "signed_by_unicef_date": datetime.date.today(),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["signed_by_partner_date"], ["signed_by_partner_date and partner_manager must be provided."])
        self.assertEquals(response.data["partner_manager"], ["partner_manager and signed_by_partner_date must be provided."])
        self.assertEquals(response.data["signed_by_unicef_date"], ["signed_by_unicef_date and signed_by must be provided."])
        self.assertEquals(response.data["signed_by"], ["signed_by and signed_by_unicef_date must be provided."])
        self.assertEquals(response.data["start"], ["Start date must be provided along with end date.", "Start date must equal to the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date)."])

    def test_agreements_update_validation_signed_date(self):
        data = {
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["signed_by_partner_date"], ["signed_by_partner_date and partner_manager must be provided."])
        self.assertEquals(response.data["partner_manager"], ["partner_manager and signed_by_partner_date must be provided."])
        self.assertEquals(response.data["signed_by_unicef_date"], ["signed_by_unicef_date and signed_by must be provided."])
        self.assertEquals(response.data["signed_by"], ["signed_by and signed_by_unicef_date must be provided."])

    def test_agreements_update_validation_end_date_pca(self):
        data = {
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
            "signed_by_partner_date": datetime.date.today(),
            "signed_by_unicef_date": datetime.date.today(),
            "start": datetime.date.today(),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["end"], str(self.country_programme.to_date))

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
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["start"], ["Start date must equal to the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date)."])

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
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["partner"], ["Partner type must be CSO for PCA or SSFA agreement types."])

    def test_agreements_update_set_to_active_on_save(self):
        today = datetime.date.today()
        data = {
            "start": date(today.year, 3, 1),
            "end": date(today.year, 6, 1),
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
            "signed_by_partner_date": date(today.year, 2, 1),
            "signed_by_unicef_date": date(today.year, 3, 1),
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
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
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["status"], "suspended")
        self.assertEquals(Intervention.objects.get(agreement=self.agreement).status, "suspended")


class TestPartnerStaffMemberAPIView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(partner_type="Civil Society Organization")
        self.partner_staff = PartnerStaffFactory(partner=self.partner)
        self.partner_staff_user = UserFactory(is_staff=True)
        self.partner_staff_user.groups.add(GroupFactory())
        self.partner_staff_user.profile.partner_staff_member = self.partner_staff.id
        self.partner_staff_user.profile.save()

    def test_partner_retrieve_embedded_staffmembers(self):
        response = self.forced_auth_req(
            'get',
            '/api/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn("Partner", response.data["name"])
        self.assertEquals("Mace", response.data["staff_members"][0]["first_name"])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_create_non_active(self):
        data = {
            "email": "a@aaa.com",
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar"
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/staff-members/',
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data["non_field_errors"], ["New Staff Member needs to be active at the moment of creation"])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_create_already_partner(self):
        partner = PartnerFactory(partner_type="Civil Society Organization")
        partner_staff = PartnerStaffFactory(partner=partner)
        partner_staff_user = UserFactory(is_staff=True)
        partner_staff_user.profile.partner_staff_member = partner_staff.id
        partner_staff_user.profile.save()
        data = {
            "email": partner_staff_user.email,
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar",
            "active": True
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/staff-members/',
            user=partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The Partner Staff member you are trying to add is associated with a different partnership", response.data["non_field_errors"][0])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_create(self):
        data = {
            "email": "a@aaa.com",
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar",
            "active": True,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/staff-members/',
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["first_name"], "Mace")

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_update(self):
        data = {
            "email": self.partner_staff.email,
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar updated",
            "active": True,
        }
        response = self.forced_auth_req(
            'put',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["title"], "foobar updated")

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_update_email(self):
        data = {
            "email": "a@a.com",
            "partner": self.partner.id,
            "first_name": "John",
            "last_name": "Doe",
            "title": "foobar updated",
            "active": True,
        }
        response = self.forced_auth_req(
            'put',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("User emails cannot be changed, please remove the user and add another one",
                      response.data["non_field_errors"][0])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_retrieve_properties(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/staff-members/{}/properties/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)

# TODO Remove after implementing InterventionTests
# class TestPCAViews(APITenantTestCase):
#
#     def setUp(self):
#         self.unicef_staff = UserFactory(is_staff=True)
#         self.partner = PartnerFactory()
#         self.agreement = AgreementFactory()
#         self.pca = PCA.objects.create(
#                                 partner=self.partner,
#                                 agreement=self.agreement,
#                                 title="PCA 1",
#                                 initiation_date=datetime.date.today(),
#                                 status=PCA.DRAFT,
#                             )
#
#     def test_pca_list(self):
#         response = self.forced_auth_req(
#             'get',
#             '/api/v2/interventions/',
#             user=self.unicef_staff
#         )
#
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertEquals(len(response.data), 1)
#
#     def test_pca_retrieve(self):
#         response = self.forced_auth_req(
#             'get',
#             '/api/v2/interventions/{}/'.format(self.pca.id),
#             user=self.unicef_staff
#         )
#
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertEquals(response.data["id"], self.pca.id)
#
#     def test_pca_create_errors(self):
#         today = datetime.date.today()
#         data = {
#             "partner": self.partner.id,
#             "title": "PCA 2",
#             "agreement": self.agreement.id,
#             "initiation_date": datetime.date.today(),
#             "status": PCA.ACTIVE,
#             "signed_by_unicef_date": datetime.date(today.year-1, 1, 1),
#             "signed_by_partner_date": datetime.date(today.year-2, 1, 1),
#             "budget_log": [],
#         }
#         response = self.forced_auth_req(
#             'post',
#             '/api/v2/interventions/',
#             user=self.unicef_staff,
#             data=data,
#         )
#
#         self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertEquals(response.data["partnership_type"], ["This field is required.","This field must be PD or SHPD in case of agreement is PCA."])
#         self.assertEquals(response.data["office"], ["This field is required."])
#         self.assertEquals(response.data["programme_focal_points"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])
#         self.assertEquals(response.data["unicef_managers"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])
#         self.assertEquals(response.data["partner_focal_point"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])
#         self.assertEquals(response.data["start_date"], ["This field is required."])
#         self.assertEquals(response.data["end_date"], ["This field is required."])
#         self.assertEquals(response.data["signed_by_unicef_date"], ["signed_by_unicef_date and unicef_manager must be provided."])
#         self.assertEquals(response.data["signed_by_partner_date"], ["signed_by_partner_date and partner_manager must be provided."])
#         self.assertEquals(response.data["partner_manager"], ["partner_manager and signed_by_partner_date must be provided."])
#         self.assertEquals(response.data["unicef_manager"], ["unicef_manager and signed_by_unicef_date must be provided."])
#         self.assertEquals(response.data["population_focus"], ["This field is required if PCA status is ACTIVE or IMPLEMENTED."])
#
#     def test_pca_create_update(self):
#         today = datetime.date.today()
#         partner_staff = PartnerStaffFactory(partner=self.partner)
#         supply_item = SupplyItem.objects.create(name="Item1")
#         sector = Sector.objects.create(name="Sector1")
#         pcasector = {
#             "sector": sector.id,
#         }
#         supply_plan = {
#             "item": supply_item.id,
#             "quantity": 5,
#         }
#         budget_log = {
#             "year": today.year,
#             "partner_contribution": 1000,
#             "unicef_cash": 1000,
#         }
#         distribution_plan = {
#             "item": supply_item.id,
#             "site": LocationFactory().id,
#             "quantity": 5,
#         }
#         amendment_log = {
#             "amended_at": today,
#             "type": "Change in Programme Result",
#         }
#         unicef_manager = UserFactory()
#         result_structure = ResultStructureFactory()
#         office = OfficeFactory()
#         location = LocationFactory()
#         gwpcalocation = {
#             "location": location.id,
#         }
#         visit = {
#             "year": 2016,
#             "programmatic": 1,
#             "spot_checks": 1,
#             "audit": 1,
#         }
#         data = {
#             "partner": self.partner.id,
#             "title": "PCA 2",
#             "agreement": self.agreement.id,
#             "initiation_date": datetime.date.today(),
#             "status": PCA.ACTIVE,
#             "partnership_type": PCA.PD,
#             "result_structure": result_structure.id,
#             "office": [office.id],
#             "programme_focal_points": [UserFactory().id],
#             "unicef_managers": [unicef_manager.id],
#             "partner_focal_point": [partner_staff.id],
#             "partner_manager": partner_staff.id,
#             "unicef_manager": self.unicef_staff.id,
#             "start_date": today,
#             "end_date": datetime.date(today.year+1, 1, 1),
#             "signed_by_unicef_date": datetime.date(today.year-1, 1, 1),
#             "signed_by_partner_date": datetime.date(today.year-2, 1, 1),
#             "population_focus": "focus1",
#             "pcasectors": [pcasector],
#             "locations": [gwpcalocation],
#             "budget_log": [budget_log],
#             "supply_plans": [supply_plan],
#             "distribution_plans": [distribution_plan],
#             "fr_numbers": ["Grant"],
#             "amendments_log": [amendment_log],
#             "visits": [visit],
#         }
#         response = self.forced_auth_req(
#             'post',
#             '/api/v2/interventions/',
#             user=self.unicef_staff,
#             data=data,
#         )
#
#         self.assertEquals(response.status_code, status.HTTP_201_CREATED)
#
#         # Test updates
#         data = response.data
#         data.update(budget_log=[budget_log, budget_log])
#         data.update(supply_plans=[supply_plan, supply_plan])
#         data.update(distribution_plans=[distribution_plan, distribution_plan])
#         data.update(amendments_log=[amendment_log, amendment_log])
#         data.update(pcasectors=[pcasector, pcasector])
#         data.update(locations=[gwpcalocation, gwpcalocation])
#         data.update(fr_numbers=["Grant", "WBS"])
#         data.update(visits=[visit, visit])
#
#         response = self.forced_auth_req(
#             'put',
#             '/api/v2/interventions/{}/'.format(data["id"]),
#             user=self.unicef_staff,
#             data=data,
#         )
#
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertEquals(len(response.data["budget_log"]), 2)
#         self.assertEquals(len(response.data["supply_plans"]), 2)
#         self.assertEquals(len(response.data["distribution_plans"]), 2)
#         self.assertEquals(len(response.data["amendments_log"]), 2)
#         self.assertEquals(len(response.data["pcasectors"]), 2)
#         self.assertEquals(len(response.data["locations"]), 2)
#         self.assertEquals(len(response.data["fr_numbers"]), 2)
#         self.assertEquals(len(response.data["visits"]), 2)
#
#         # Test filter
#         params = {
#             "partnership_type": PCA.PD,
#             "sector": sector.id,
#             "location": location.id,
#             "status": PCA.ACTIVE,
#             "unicef_managers": unicef_manager.id,
#             "start_date": datetime.date(today.year-1, 1, 1),
#             "end_date": datetime.date(today.year+1, 1, 1),
#             "office": office.id,
#             "search": "PCA 2",
#         }
#         response = self.forced_auth_req(
#             'get',
#             '/api/v2/interventions/',
#             user=self.unicef_staff,
#             data=params
#         )
#
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertEquals(response.data[0]["id"], data["id"])
