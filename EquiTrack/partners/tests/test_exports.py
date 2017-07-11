from __future__ import unicode_literals
import datetime
import tempfile
from rest_framework import status
from tablib.core import Dataset

from EquiTrack.factories import UserFactory, PartnerFactory, AgreementFactory, \
    GovernmentInterventionFactory, InterventionFactory, CountryProgrammeFactory, ResultFactory, \
    ResultStructureFactory, InterventionBudgetFactory, PartnerStaffFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import CurrencyFactory
from partners.models import GovernmentInterventionResult, SupplyPlan, DistributionPlan
from reports.models import ResultType
from supplies.models import SupplyItem


class TestModelExport(APITenantTestCase):
    def setUp(self):
        super(TestModelExport, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(
            partner_type='Government',
            vendor_number='Vendor No',
            short_name="Short Name",
            alternate_name="Alternate Name",
            shared_with=["DPKO", "ECA"],
            address="Address 123",
            phone_number="Phone no 1234567",
            email="email@address.com",
            rating="High",
            core_values_assessment_date=datetime.date.today(),
            total_ct_cp=10000,
            total_ct_cy=20000,
            deleted_flag=False,
            blocked=False,
            type_of_assessment="Type of Assessment",
            last_assessment_date=datetime.date.today(),
        )
        self.partnerstaff = PartnerStaffFactory(partner=self.partner)
        attachment = tempfile.NamedTemporaryFile(suffix=".pdf").name
        self.agreement = AgreementFactory(
            partner=self.partner,
            country_programme=CountryProgrammeFactory(wbs="random WBS"),
            attached_agreement=attachment,
            start=datetime.date.today(),
            end=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by=self.unicef_staff,
            signed_by_partner_date=datetime.date.today()
        )
        self.agreement.authorized_officers.add(self.partnerstaff)
        self.agreement.save()
        # This is here to test partner scoping
        AgreementFactory(signed_by_unicef_date=datetime.date.today())
        self.intervention = InterventionFactory(
            agreement=self.agreement,
            document_type='SHPD',
            hrp=ResultStructureFactory(),
            status='draft',
            start=datetime.date.today(),
            end=datetime.date.today(),
            submission_date=datetime.date.today(),
            submission_date_prc=datetime.date.today(),
            review_date_prc=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            unicef_signatory=self.unicef_staff,
            population_focus="Population focus",
            fr_numbers=["1234", "124456"],
            partner_authorized_officer_signatory=self.partnerstaff,
        )
        self.supply_item = SupplyItem.objects.create(name="foo", description="bar")
        self.supplyplan = SupplyPlan.objects.create(
            intervention=self.intervention,
            quantity=1,
            item=self.supply_item
        )
        self.distributionplan = DistributionPlan.objects.create(
            intervention=self.intervention,
            item=self.supply_item,
            quantity=1
        )
        self.ib = InterventionBudgetFactory(intervention=self.intervention, currency=CurrencyFactory())
        self.government_intervention = GovernmentInterventionFactory(
            partner=self.partner,
            country_programme=self.agreement.country_programme
        )

        output_res_type, _ = ResultType.objects.get_or_create(name='Output')
        self.result = ResultFactory(result_type=output_res_type)
        self.govint_result = GovernmentInterventionResult.objects.create(
            intervention=self.government_intervention,
            result=self.result,
            year=datetime.date.today().year,
            planned_amount=100,
        )

    def test_intervention_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Status',
            'Partner',
            'Partner Type',
            'Agreement',
            'Country Programme',
            'Document Type',
            'Reference Number',
            'Document Title',
            'Start Date',
            'End Date',
            'UNICEF Office',
            'Sectors',
            'Locations',
            'UNICEF Focal Points',
            'CSO Authorized Officials',
            'Population Focus',
            'Humanitarian Response Plan',
            'CP Outputs',
            'RAM Indicators',
            'FR Number(s)',
            'Local Currency of Planned Budget',
            'Total UNICEF Budget (Local)',
            'Total UNICEF Budget (USD)',
            'Total CSO Budget (USD)',
            'Total CSO Budget (Local)',
            'Planned Programmatic Visits',
            'Planned Spot Checks',
            'Planned Audits',
            'Document Submission Date by CSO',
            'Submission Date to PRC',
            'Review Date by PRC',
            'Signed by Partner',
            'Signed by Partner Date',
            'Signed by UNICEF',
            'Signed by UNICEF Date',
            'Days from Submission to Signed',
            'Days from Review to Signed',
            'URL'
        ])

        self.assertEqual(dataset[0], (
            self.intervention.status,
            unicode(self.intervention.agreement.partner.name),
            self.intervention.agreement.partner.partner_type,
            self.intervention.agreement.agreement_number,
            unicode(self.intervention.agreement.country_programme.name),
            self.intervention.document_type,
            self.intervention.reference_number,
            unicode(self.intervention.title),
            '{}'.format(self.intervention.start),
            '{}'.format(self.intervention.end),
            u'',
            u'',
            u'',
            u'',
            u'',
            self.intervention.population_focus,
            unicode(self.intervention.hrp.name),
            u'',
            u'',
            u', '.join(self.intervention.fr_numbers),
            '{}'.format(self.intervention.planned_budget.first().currency),
            u'{:.2f}'.format(self.intervention.total_unicef_cash_local),
            u'{:.2f}'.format(self.intervention.total_unicef_budget),
            u'{:.2f}'.format(self.intervention.total_partner_contribution),
            u'{:.2f}'.format(self.intervention.total_partner_contribution_local),
            u'',
            u'',
            u'',
            '{}'.format(self.intervention.submission_date),
            '{}'.format(self.intervention.submission_date_prc),
            '{}'.format(self.intervention.review_date_prc),
            u'{}'.format(self.intervention.partner_authorized_officer_signatory.get_full_name()),
            '{}'.format(self.intervention.signed_by_unicef_date),
            u'',
            '{}'.format(self.intervention.signed_by_partner_date),
            '{}'.format(self.intervention.days_from_submission_to_signed),
            '{}'.format(self.intervention.days_from_review_to_signed),
            u'https://testserver/pmp/interventions/{}/details/'.format(self.intervention.id)
        )
        )

    def test_agreement_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 2)
        self.assertEqual(dataset._get_headers(), [
            'Reference Number',
            'Status',
            'Partner Name',
            'Agreement Type',
            'Start Date',
            'End Date',
            'Signed By Partner',
            'Signed By Partner Date',
            'Signed By UNICEF',
            'Signed By UNICEF Date',
            'Partner Authorized Officer',
            'Amendments',
            'URL'
        ])

        self.assertEqual(dataset[0], (
            self.agreement.agreement_number,
            unicode(self.agreement.status),
            unicode(self.agreement.partner.name),
            self.agreement.agreement_type,
            '{}'.format(self.agreement.start),
            '{}'.format(self.agreement.end),
            u'',
            '{}'.format(self.agreement.signed_by_partner_date),
            u'',
            '{}'.format(self.agreement.signed_by_unicef_date),
            ', '.join([sm.get_full_name() for sm in self.agreement.authorized_officers.all()]),
            u'',
            u'https://testserver/pmp/agreements/{}/details/'.format(self.agreement.id)
        )
        )

    def test_partners_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/partners/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 2)
        self.assertEqual(dataset._get_headers(), [
            'Vendor Number',
            'Organizations Full Name',
            'Short Name',
            'Alternate Name',
            'Partner Type',
            'Shared Partner',
            'Address',
            'Phone Number',
            'Email Address',
            'Risk Rating',
            'Date Last Assessed Against Core Values',
            'Actual Cash Transfer for CP (USD)',
            'Actual Cash Transfer for Current Year (USD)',
            'Marked for Deletion',
            'Blocked',
            'Assessment Type',
            'Date Assessed',
            'Assessment Type (Date Assessed)',
            'Staff Members',
            'URL'
        ])
        deleted_flag = "Yes" if self.partner.deleted_flag else "No"
        blocked = "Yes" if self.partner.blocked else "No"

        self.assertEqual(dataset[0], (
            self.partner.vendor_number,
            unicode(self.partner.name),
            self.partner.short_name,
            self.partner.alternate_name,
            "{}".format(self.partner.partner_type),
            u', '.join([x for x in self.partner.shared_with]),
            self.partner.address,
            self.partner.phone_number,
            self.partner.email,
            self.partner.rating,
            u'{}'.format(self.partner.core_values_assessment_date),
            u'{:.2f}'.format(self.partner.total_ct_cp),
            u'{:.2f}'.format(self.partner.total_ct_cy),
            deleted_flag,
            blocked,
            self.partner.type_of_assessment,
            u'{}'.format(self.partner.last_assessment_date),
            u'',
            ', '.join(["{} ({})".format(sm.get_full_name(), sm.email)
                       for sm in self.partner.staff_members.filter(active=True).all()]),
            u'https://testserver/pmp/partners/{}/details/'.format(self.partner.id)
        )
        )
