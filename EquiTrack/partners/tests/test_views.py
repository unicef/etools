__author__ = 'unicef-leb-inn'

from unittest import skip
import datetime
from datetime import date, timedelta

from rest_framework import status

from actstream.models import model_stream

from EquiTrack.factories import (
    PartnerFactory,
    UserFactory,
    ResultFactory,
    ResultStructureFactory,
    LocationFactory,
    AgreementFactory,
    PartnerStaffFactory,
    CountryProgrammeFactory,
    GroupFactory,
    InterventionFactory,
    GovernmentInterventionFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase
from reports.models import ResultType, Sector, CountryProgramme
from funds.models import FundsCommitmentItem, FundsCommitmentHeader
from partners.models import (
    Agreement,
    PartnerType,
    Intervention,
    InterventionSectorLocationLink,
    InterventionBudget,
    InterventionAmendment,
    GovernmentInterventionResult,
    AgreementAmendment,
    AgreementAmendmentType,
    Assessment,
    InterventionPlannedVisits,
    InterventionAttachment,
    FileType,
    InterventionResultLink,
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
        report = "report.pdf"
        self.assessment1 = Assessment.objects.create(
            partner=self.partner,
            type="Micro Assessment"
        )
        self.assessment2 = Assessment.objects.create(
            partner=self.partner,
            type="Micro Assessment",
            report=report,
            completed_date=datetime.date.today()
        )

        self.partner_gov = PartnerFactory(partner_type="Government")

        agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today())

        self.intervention = InterventionFactory(agreement=agreement)
        self.output_res_type, _ = ResultType.objects.get_or_create(name='Output')

        self.result = ResultFactory(
            result_type=self.output_res_type,
            result_structure=ResultStructureFactory())
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
            type="Change in Programme Result"
        )
        self.location = InterventionSectorLocationLink.objects.create(
            intervention=self.intervention,
            sector=Sector.objects.create(name="Sector 2")
        )
        self.cp = CountryProgrammeFactory(wbs="WBS ", __sequence=10)
        self.cp_output = ResultFactory(result_type=self.output_res_type)
        self.govint = GovernmentInterventionFactory(
            partner=self.partner_gov,
            country_programme=self.cp
        )
        self.result = ResultFactory()
        self.govint_result = GovernmentInterventionResult.objects.create(
            intervention=self.govint,
            result=self.result,
            year=datetime.date.today().year,
            planned_amount=100,
        )

    def test_api_partners_delete_asssessment_valid(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/partners/assessments/{}/'.format(self.assessment1.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_api_partners_delete_asssessment_error(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/partners/assessments/{}/'.format(self.assessment2.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete a completed assessment"])

    def test_api_partners_list_restricted(self):
        response = self.forced_auth_req('get', '/api/v2/partners/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_api_partners_update_with_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 1)
        self.assertEqual(response.data["staff_members"][0]["first_name"], "Mace")

        staff_members = [{
            "title": "Some title",
            "first_name": "John",
            "last_name": "Doe",
            "email": "a@a.com",
            "active": True,
        }]
        data = {
            "name": self.partner.name + ' Updated',
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 2)

    def test_api_partners_update_assessments_invalid(self):
        today = datetime.date.today()
        assessments = [{
                "id": self.assessment2.id,
                "completed_date": datetime.date(today.year + 1, 1, 1),
            }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"assessments":
                                          {"completed_date":
                                           ["The Date of Report cannot be in the future"]}})

    def test_api_partners_update_assessments_longago(self):
        today = datetime.date.today()
        assessments = [{
                "id": self.assessment2.id,
                "completed_date": datetime.date(today.year - 3, 1, 1),
            }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_partners_update_assessments_today(self):
        completed_date = datetime.date.today()
        assessments = [{
                "id": self.assessment2.id,
                "completed_date": completed_date,
            }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_partners_update_assessments_yesterday(self):
        completed_date = datetime.date.today() - timedelta(days=1)
        assessments = [{
                "id": self.assessment2.id,
                "completed_date": completed_date,
            }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_partners_update_with_members_null_phone(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["staff_members"]), 1)
        self.assertEqual(response.data["staff_members"][0]["first_name"], "Mace")

        staff_members = [{
            "title": "Some title",
            "first_name": "John",
            "last_name": "Doe",
            "email": "a1@a.com",
            "active": True,
            "phone": None
        }]
        data = {
            "staff_members": staff_members,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["staff_members"][1]["phone"], None)

    def test_api_partners_update_assessments_tomorrow(self):
        completed_date = datetime.date.today() + timedelta(days=1)
        assessments = [{
                "id": self.assessment2.id,
                "completed_date": completed_date,
            }]
        data = {
            "assessments": assessments,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"assessments":
                                          {"completed_date":
                                           ["The Date of Report cannot be in the future"]}})

    def test_api_partners_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("vendor_number", response.data.keys())
        self.assertIn("address", response.data.keys())
        self.assertIn("Partner", response.data["name"])
        self.assertEqual(['programme_visits', 'spot_checks'], response.data["hact_min_requirements"].keys())
        self.assertEqual(['audits_done', 'planned_visits', 'spot_checks', 'programmatic_visits', 'follow_up_flags',
                           'planned_cash_transfer', 'micro_assessment_needed', 'audits_mr'], response.data["hact_values"].keys())
        self.assertEqual(response.data['interventions'], [])

    def test_api_partners_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("staff_members", response.data.keys())
        self.assertEqual(len(response.data["staff_members"]), 1)

    def test_api_partners_update(self):
        data = {
            "name": "Updated name again",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Updated", response.data["name"])

    def test_api_partners_list_minimal(self):
        params = {"verbosity": "minimal"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].keys(), ["id", "name"])

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.partner.id)
        self.assertEqual(response.data[0]["partner_type"], PartnerType.CIVIL_SOCIETY_ORGANIZATION)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.partner.id)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], self.partner.id)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], self.partner.id)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.partner.id)

    def test_api_partners_values(self):
        # make some other instance to filter against
        p1 = PartnerFactory()
        p2 = PartnerFactory()
        params = {"values": "{},{}".format(p1.id, p2.id)}
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], p1.id)
        self.assertEqual(response.data[1]["id"], p2.id)


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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
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
            '/api/v2/partners/' + str(self.partner.id) + '/agreements/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @skip("different endpoint")
    def test_api_agreements_list(self):

        response = self.forced_auth_req('get', '/api/partners/' + str(self.partner.id) +
                                        '/agreements/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("PCA", response.data[0]["agreement_type"])

    def test_api_staffmembers_list(self):
        response = self.forced_auth_req('get',
                                        '/'.join(['/api/partners', str(self.partner.id), 'staff-members/']),
                                        user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["unicef_cash"], 100)
        self.assertEqual(response.data[0]["total"], 100)

    @skip("different endpoint")
    def test_api_interventions_files_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join([
                                            '/api/partners',
                                            str(self.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'files/'
                                        ]), user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["type"], "Cost")

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
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

        attached_agreement = "agreement.pdf"
        self.agreement = AgreementFactory(
            partner=self.partner,
            partner_manager=self.partner_staff,
            start=datetime.date.today(),
            end=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            signed_by=self.unicef_staff,
            attached_agreement=attached_agreement,
        )
        self.agreement.authorized_officers.add(self.partner_staff)
        self.agreement.save()
        today = datetime.date.today()
        self.country_programme = CountryProgrammeFactory(
            wbs='/A0/',
            from_date=date(today.year - 1, 1, 1),
            to_date=date(today.year + 1, 1, 1))
        self.amendment1 = AgreementAmendment.objects.create(
            number="001",
            agreement=self.agreement,
            signed_amendment="application/pdf",
            signed_date=datetime.date.today(),
        )
        self.amendment2 = AgreementAmendment.objects.create(
            number="002",
            agreement=self.agreement,
            signed_amendment="application/pdf",
        )
        self.amendment_type1 = AgreementAmendmentType.objects.create(
            agreement_amendment=self.amendment1,
            type="CP extension"
        )
        self.amendment_type2 = AgreementAmendmentType.objects.create(
            agreement_amendment=self.amendment2,
            type="CP extension"
        )
        self.agreement2 = AgreementFactory(
            partner=self.partner,
            agreement_type="MOU",
            status="draft"
        )
        self.intervention = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD)

    def test_agreements_create(self):
        today = datetime.date.today()
        data = {
            "agreement_type": "PCA",
            "partner": self.partner.id,
            "status": "draft",
            "start": date(today.year - 1, 1, 1),
            "end": date(today.year - 1, 6, 1),
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
            "signed_by_partner_date": date(today.year - 1, 1, 1),
            "signed_by_unicef_date": date(today.year - 1, 1, 1),
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check for activity action created
        self.assertEqual(model_stream(Agreement).count(), 1)
        self.assertEqual(model_stream(Agreement)[0].verb, 'created')
        self.assertEqual(model_stream(Agreement)[0].target.start, date(today.year - 1, 1, 1))

    def test_agreements_create_max_signoff_single_date(self):
        today = datetime.date.today()
        data = {
            "agreement_type": "PCA",
            "partner": self.partner.id,
            "status": "draft",
            "start": date(today.year - 1, 1, 1),
            "end": date(today.year - 1, 6, 1),
            "signed_by": self.unicef_staff.id,
            "signed_by_unicef_date": date(today.year - 1, 1, 1),
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_agreements_create_max_signoff_no_date(self):
        today = datetime.date.today()
        data = {
            "agreement_type": "PCA",
            "partner": self.partner.id,
            "status": "draft",
            "start": date(today.year - 1, 1, 1),
            "end": date(today.year - 1, 6, 1),
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.partner_staff_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_agreements_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])

    def test_agreements_update(self):
        data = {
            "status": "active",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "active")

        # There should not be any activity stream item created as there is no delta data
        self.assertEqual(model_stream(Agreement).count(), 0)

    def test_agreements_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["agreement_number"], self.agreement.agreement_number)

    def test_agreements_retrieve_staff_members(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["authorized_officers"][0]["first_name"], self.partner_staff.first_name)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["authorized_officers"]), 2)

        # Check for activity action created
        self.assertEqual(model_stream(Agreement).count(), 1)
        self.assertEqual(model_stream(Agreement)[0].verb, 'changed')

    def test_agreements_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agreements_list_filter_type(self):
        params = {"agreement_type": "PCA"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.agreement.id)
        self.assertEqual(response.data[0]["agreement_type"], "PCA")

    def test_agreements_list_filter_status(self):
        params = {"status": "active"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.agreement.id)
        self.assertEqual(response.data[0]["status"], "active")

    def test_agreements_list_filter_partner_name(self):
        params = {"partner_name": self.partner.name}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(self.partner.name, response.data[0]["partner_name"])

    def test_agreements_list_filter_search(self):
        params = {"search": "Partner"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("Partner", response.data[0]["partner_name"])

    def test_agreements_list_filter_search_refno(self):
        params = {"search": datetime.date.today().year}
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/'.format(self.partner.id),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # self.assertEquals(response.data[1]["agreement_number"], self.agreement.agreement_number)

    @skip("Test transitions - checked when going active")
    def test_agreements_create_validation_signed_by(self):
        data = {
            "agreement_type": "PCA",
            "partner": self.partner.id,
            "status": "draft",
            "start": datetime.date.today(),
            "end": datetime.date.today(),
            "signed_by_partner_date": datetime.date.today(),
            "signed_by_unicef_date": datetime.date.today(),
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["errors"], ["Partner manager and signed by must be provided."])

    def test_agreements_create_start_set_to_max_signed(self):
        today = datetime.date.today()
        data = {
            "agreement_type": "PCA",
            "partner": self.partner.id,
            "status": "draft",
            "start": date(today.year - 1, 1, 1),
            "end": date(today.year - 1, 6, 1),
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
            "signed_by_partner_date": date(today.year - 1, 2, 1),
            "signed_by_unicef_date": date(today.year - 1, 3, 1),
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["errors"],
            ["Start date must equal to the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date)."])

    def test_agreements_create_PCA_must_be_CSO(self):
        self.partner.partner_type = "Government"
        self.partner.save()
        data = {
            "agreement_type": "PCA",
            "partner": self.partner.id,
            "status": "draft",
            "signed_by": self.unicef_staff.id,
            "partner_manager": self.partner_staff.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/agreements/',
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["errors"], ["Partner type must be CSO for PCA or SSFA agreement types."])

    @skip("Test transitions")
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Agreement.ACTIVE)

    @skip("Test transitions")
    def test_partner_agreements_update_suspend(self):
        data = {
            "status": "suspended",
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/agreements/{}/'.format(self.agreement.id),
            user=self.partnership_manager_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "suspended")
        self.assertEqual(Intervention.objects.get(agreement=self.agreement).status, "suspended")

    def test_partner_agreement_amendment_cp_cycle_end(self):
        amendment_type = AgreementAmendmentType.objects.create(
            agreement_amendment=self.amendment1,
            type="CP extension"
        )

        self.assertEqual(amendment_type.cp_cycle_end, CountryProgramme.current().to_date)

    @skip("signed amendment is now mandatory so we cannot delete?")
    def test_agreement_amendment_delete_valid(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/amendments/{}/'.format(self.agreement.amendments.last().id),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agreement_amendment_delete_error(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/amendments/{}/'.format(self.agreement.amendments.first().id),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete a signed amendment"])

    @skip("signed amendment is now mandatory so we cannot delete?")
    def test_agreement_amendment_type_delete_valid(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/amendments/types/{}/'.format(self.amendment_type2.id),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agreement_amendment_delete_error_signed(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/agreements/amendments/types/{}/'.format(self.amendment_type1.id),
            user=self.partnership_manager_user,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot delete an amendment type once amendment is signed"])


class TestPartnerStaffMemberAPIView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(partner_type="Civil Society Organization")
        self.partner_staff = PartnerStaffFactory(partner=self.partner)
        self.partner_staff_user = UserFactory(is_staff=True)
        self.partner_staff_user.groups.add(GroupFactory())
        self.partner_staff_user.profile.partner_staff_member = self.partner_staff.id
        self.partner_staff_user.profile.save()

    @skip("different endpoint")
    def test_partner_retrieve_embedded_staffmembers(self):
        response = self.forced_auth_req(
            'get',
            '/api/partners/{}/'.format(self.partner.id),
            user=self.unicef_staff
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Partner", response.data["name"])
        self.assertEqual("Mace", response.data["staff_members"][0]["first_name"])

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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"],
                          ["New Staff Member needs to be active at the moment of creation"])

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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "The Partner Staff member you are trying to add is associated with a different partnership",
            response.data["non_field_errors"][0])

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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_retrieve(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Mace")

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "foobar updated")

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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("User emails cannot be changed, please remove the user and add another one",
                      response.data["non_field_errors"][0])

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/staff-members/{}/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @skip("Skip staffmembers for now")
    def test_partner_staffmember_retrieve_properties(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/staff-members/{}/properties/'.format(self.partner_staff.id),
            user=self.partner_staff_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestInterventionViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.agreement = AgreementFactory()
        self.agreement2 = AgreementFactory(status="draft")
        self.partnerstaff = PartnerStaffFactory(partner=self.agreement.partner)
        data = {
            "document_type": Intervention.SHPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP",
            "start": "2016-10-28",
            "end": "2016-10-28",
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=data
        )
        self.intervention = response.data

        self.sector = Sector.objects.create(name="Sector 1")
        self.location = LocationFactory()
        self.isll = InterventionSectorLocationLink.objects.create(
            intervention=Intervention.objects.get(id=self.intervention["id"]),
            sector=self.sector,
        )
        self.isll.locations.add(LocationFactory())
        self.isll.save()
        self.fund_commitment_header = FundsCommitmentHeader.objects.create(
            vendor_code="test1",
            fc_number="3454354",
        )

        self.funding_commitment1 = FundsCommitmentItem.objects.create(
            fund_commitment=self.fund_commitment_header,
            line_item="1",
            grant_number="grant 1",
            fr_number="12345",
            wbs="some_wbs",
            fc_ref_number="some_fc_ref",
            commitment_amount=200,
        )

        self.funding_commitment2 = FundsCommitmentItem.objects.create(
            fund_commitment=self.fund_commitment_header,
            line_item="2",
            grant_number="grant 1",
            fr_number="45678",
            wbs="some_wbs",
            fc_ref_number="some_fc_ref",
            commitment_amount=300,
        )

        # Basic data to adjust in tests
        self.intervention_data = {
            "agreement": self.agreement2.id,
            "partner_id": self.agreement2.partner.id,
            "document_type": Intervention.SHPD,
            "hrp": ResultStructureFactory().id,
            "title": "2009 EFY AWP Updated",
            "status": "draft",
            "start": "2016-10-28",
            "end": "2016-10-28",
            "submission_date_prc": "2016-10-31",
            "review_date_prc": "2016-10-28",
            "submission_date": "2016-10-28",
            "prc_review_document": None,
            "signed_by_unicef_date": "2016-10-28",
            "signed_by_partner_date": "2016-10-20",
            "unicef_signatory": self.unicef_staff.id,
            "unicef_focal_points": [],
            "partner_focal_points": [],
            "partner_authorized_officer_signatory": self.partnerstaff.id,
            "offices": [],
            "fr_numbers": [
                self.funding_commitment1.fr_number,
                self.funding_commitment2.fr_number
            ],
            "population_focus": "Some focus",
            "planned_visits": [
                {
                    "year": 2016,
                    "programmatic": 2,
                    "spot_checks": 1,
                    "audit": 1
                },
            ],
            "planned_budget": [
                {
                    "partner_contribution": "2.00",
                    "unicef_cash": "3.00",
                    "in_kind_amount": "1.00",
                    "partner_contribution_local": "3.00",
                    "unicef_cash_local": "3.00",
                    "in_kind_amount_local": "0.00",
                    "year": "2017",
                    "total": "6.00"
                },
                {
                    "partner_contribution": "2.00",
                    "unicef_cash": "3.00",
                    "in_kind_amount": "1.00",
                    "partner_contribution_local": "3.00",
                    "unicef_cash_local": "3.00",
                    "in_kind_amount_local": "0.00",
                    "year": "2016",
                    "total": "6.00"
                }
            ],
            "sector_locations": [
                {
                    "sector": self.sector.id,
                    "locations": [self.location.id],
                }
            ],
            "result_links": [
                {
                    "cp_output": ResultFactory().id,
                    "ram_indicators": []
                }
            ],
            "amendments": [],
            "attachments": [],
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=self.intervention_data
        )
        self.intervention_data = response.data
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        self.planned_visit = InterventionPlannedVisits.objects.create(
            intervention=intervention_obj
        )
        attachment = "attachment.pdf"
        self.attachment = InterventionAttachment.objects.create(
            intervention=intervention_obj,
            attachment=attachment,
            type=FileType.objects.create(name="pdf")
        )
        self.result = InterventionResultLink.objects.create(
            intervention=intervention_obj,
            cp_output=ResultFactory(),
        )
        amendment = "amendment.pdf"
        self.amendment = InterventionAmendment.objects.create(
            intervention=intervention_obj,
            type="Change in Programme Result",
            signed_date=datetime.date.today(),
            signed_amendment=amendment
        )
        self.sector = Sector.objects.create(name="Sector 2")
        self.location = LocationFactory()
        self.isll = InterventionSectorLocationLink.objects.create(
            intervention=intervention_obj,
            sector=self.sector,
        )
        self.isll.locations.add(LocationFactory())
        self.isll.save()
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()

    def test_intervention_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_intervention_list_minimal(self):
        params = {"verbosity": "minimal"}
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].keys(), ["id", "title"])

    def test_intervention_create(self):
        data = {
            "document_type": Intervention.SHPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP Updated",
            "start": "2016-10-28",
            "end": "2016-10-28",
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check for activity action created
        self.assertEqual(model_stream(Intervention).count(), 3)
        self.assertEqual(model_stream(Intervention)[0].verb, 'created')

    def test_intervention_retrieve_fr_numbers(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fr_numbers_details"]["12345"][0]["wbs"], "some_wbs")
        self.assertEqual(response.data["fr_numbers_details"]["45678"][0]["wbs"], "some_wbs")

    def test_intervention_active_update_population_focus(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        self.intervention_data.update(population_focus=None)
        self.intervention_data.update(status="active")
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
            data=self.intervention_data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_intervention_active_update_planned_budget(self):
        InterventionBudget.objects.filter(intervention=self.intervention_data.get("id")).delete()
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        self.intervention_data.update(status='active')
        self.intervention_data.update(planned_budget=[])
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Planned budget is required if Intervention status is ACTIVE or IMPLEMENTED."])

    @skip('Add test back after reintroducing active validations')
    def test_intervention_active_update_planned_budget_rigid(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.ACTIVE
        intervention_obj.save()
        self.intervention_data["planned_budget"][0].update(unicef_cash=0)
        self.intervention_data["planned_budget"][1].update(unicef_cash=0)
        self.intervention_data.update(status="active")

        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Cannot change fields while intervention is active: unicef_cash"])

    def test_intervention_active_update_sector_locations(self):
        intervention_obj = Intervention.objects.get(id=self.intervention_data["id"])
        intervention_obj.status = Intervention.DRAFT
        intervention_obj.save()
        InterventionSectorLocationLink.objects.filter(intervention=self.intervention_data.get("id")).delete()
        self.intervention_data.update(sector_locations=[])
        self.intervention_data.update(status="active")
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention_data.get("id")),
            user=self.unicef_staff,
            data=self.intervention_data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Sector locations are required if Intervention status is ACTIVE or IMPLEMENTED."])

    def test_intervention_validation(self):
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data,
                          {"document_type": ["This field is required."],
                           "agreement": ["This field is required."],
                              "title": ["This field is required."]})

    def test_intervention_validation_doctype_pca(self):
        data = {
            "document_type": Intervention.SSFA,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Document type must be PD or SHPD in case of agreement is PCA."])

    def test_intervention_validation_doctype_ssfa(self):
        self.agreement.agreement_type = Agreement.SSFA
        self.agreement.save()
        data = {
            "document_type": Intervention.PD,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["Document type must be SSFA in case of agreement is SSFA."])

    def test_intervention_validation_dates(self):
        today = datetime.date.today()
        data = {
            "start": datetime.date(today.year + 1, 1, 1),
            "end": today,
        }
        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ['Start date must precede end date'])

    def test_intervention_update_planned_visits(self):
        import copy
        a = copy.deepcopy(self.intervention_data["planned_visits"])
        a.append({
            "year": 2015,
            "programmatic": 2,
            "spot_checks": 1,
            "audit": 1
        })
        data = {
            "planned_visits": a,
        }

        response = self.forced_auth_req(
            'patch',
            '/api/v2/interventions/{}/'.format(self.intervention["id"]),
            user=self.unicef_staff,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_intervention_filter(self):
        # Test filter
        params = {
            "partnership_type": Intervention.PD,
            "status": Intervention.DRAFT,
            "start": "2016-10-28",
            "end": "2016-10-28",
            "location": "Location",
            "sector": self.sector.id,
            "search": "2009",
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_intervention_filter_my_partnerships(self):
        # Test filter
        params = {
            "my_partnerships": True,
        }
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_intervention_planned_budget_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/budgets/{}/'.format(self.intervention_data["planned_budget"][0]["id"]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_planned_budget_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = "active"
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/budgets/{}/'.format(self.intervention_data["planned_budget"][0]["id"]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a planned budget"])

    def test_intervention_planned_visits_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/planned-visits/{}/'.format(self.planned_visit.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_planned_visits_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = "active"
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/planned-visits/{}/'.format(self.planned_visit.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a planned visit"])

    def test_intervention_attachments_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/attachments/{}/'.format(self.attachment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_attachments_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = "active"
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/attachments/{}/'.format(self.attachment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete an attachment"])

    def test_intervention_results_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/results/{}/'.format(self.result.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_results_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = "active"
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/results/{}/'.format(self.result.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a result"])

    def test_intervention_amendments_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/amendments/{}/'.format(self.amendment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_amendments_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = "active"
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/amendments/{}/'.format(self.amendment.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete an amendment"])

    def test_intervention_sector_locations_delete(self):
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/sector-locations/{}/'.format(self.isll.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_intervention_sector_locations_delete_invalid(self):
        intervention = Intervention.objects.get(id=self.intervention_data["id"])
        intervention.status = "active"
        intervention.save()
        response = self.forced_auth_req(
            'delete',
            '/api/v2/interventions/sector-locations/{}/'.format(self.isll.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, ["You do not have permissions to delete a sector location"])


    def test_api_interventions_values(self):
        params = {"values": "{}".format(self.intervention["id"])}
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.intervention["id"])


class TestPartnershipDashboardView(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.agreement = AgreementFactory()
        self.agreement2 = AgreementFactory(status="draft")
        self.partnerstaff = PartnerStaffFactory(partner=self.agreement.partner)
        data = {
            "document_type": Intervention.SHPD,
            "status": Intervention.DRAFT,
            "title": "2009 EFY AWP",
            "start": "2016-10-28",
            "end": "2016-10-28",
            "unicef_budget": 0,
            "agreement": self.agreement.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=data
        )
        self.intervention = response.data

        self.sector = Sector.objects.create(name="Sector 1")
        self.location = LocationFactory()
        self.isll = InterventionSectorLocationLink.objects.create(
            intervention=Intervention.objects.get(id=self.intervention["id"]),
            sector=self.sector,
        )
        self.isll.locations.add(LocationFactory())
        self.isll.save()

        # Basic data to adjust in tests
        self.intervention_data = {
            "agreement": self.agreement2.id,
            "partner_id": self.agreement2.partner.id,
            "document_type": Intervention.SHPD,
            "hrp": ResultStructureFactory().id,
            "title": "2009 EFY AWP Updated",
            "status": "draft",
            "start": "2017-01-28",
            "end": "2019-01-28",
            "submission_date_prc": "2017-01-31",
            "review_date_prc": "2017-01-28",
            "submission_date": "2017-01-28",
            "prc_review_document": None,
            "signed_by_unicef_date": "2017-01-28",
            "signed_by_partner_date": "2017-01-20",
            "unicef_signatory": self.unicef_staff.id,
            "unicef_focal_points": [],
            "partner_focal_points": [],
            "partner_authorized_officer_signatory": self.partnerstaff.id,
            "offices": [],
            "fr_numbers": None,
            "population_focus": "Some focus",
            "planned_budget": [
                {
                    "partner_contribution": "2.00",
                    "unicef_cash": "3.00",
                    "in_kind_amount": "1.00",
                    "partner_contribution_local": "3.00",
                    "unicef_cash_local": "3.00",
                    "in_kind_amount_local": "0.00",
                    "year": "2018",
                    "total": "6.00"
                },
                {
                    "partner_contribution": "2.00",
                    "unicef_cash": "3.00",
                    "in_kind_amount": "1.00",
                    "partner_contribution_local": "3.00",
                    "unicef_cash_local": "3.00",
                    "in_kind_amount_local": "0.00",
                    "year": "2017",
                    "total": "6.00"
                }
            ],
            "sector_locations": [
                {
                    "sector": self.sector.id,
                    "locations": [self.location.id],
                }
            ],
            "result_links": [
                {
                    "cp_output": ResultFactory().id,
                    "ram_indicators": []
                }
            ],
            "amendments": [],
            "attachments": [],
        }
        response = self.forced_auth_req(
            'post',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data=self.intervention_data
        )
        self.intervention_data = response.data

    def test_with_ct_pk(self):
        intervention = Intervention.objects.get(id=self.intervention_data['id'])
        intervention.status = Intervention.ACTIVE
        intervention.save()

        response = self.forced_auth_req(
            'get',
            '/api/v2/partnership-dash/{}/'.format(self.agreement2.country_programme.id),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['active_value'], 0)
        self.assertEqual(response.data['active_count'], 1)
        self.assertEqual(response.data['active_this_year_count'], 1)
        self.assertEqual(response.data['active_this_year_percentage'], '100%')
