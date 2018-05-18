# TODO this is a conflicted page.. needs checking..
import datetime
import tempfile

from django.utils import six

from rest_framework import status
from tablib.core import Dataset

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerOrganization, PartnerType
from etools.applications.partners.tests.factories import (AgreementFactory, CountryProgrammeFactory,
                                                          InterventionBudgetFactory, InterventionFactory,
                                                          PartnerFactory, PartnerPlannedVisitsFactory,
                                                          PartnerStaffFactory,)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory
from etools.applications.users.tests.factories import UserFactory


class TestModelExport(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            partner_type=PartnerType.UN_AGENCY,
            vendor_number='Vendor No',
            short_name="Short Name",
            alternate_name="Alternate Name",
            shared_with=["DPKO", "ECA"],
            address="Address 123",
            phone_number="Phone no 1234567",
            email="email@address.com",
            rating=PartnerOrganization.RATING_HIGH,
            core_values_assessment_date=datetime.date.today(),
            total_ct_cp=10000,
            total_ct_cy=20000,
            net_ct_cy=100.0,
            reported_cy=300.0,
            total_ct_ytd=400.0,
            deleted_flag=False,
            blocked=False,
            type_of_assessment="Type of Assessment",
            last_assessment_date=datetime.date.today(),
        )
        cls.partnerstaff = PartnerStaffFactory(partner=cls.partner)
        attachment = tempfile.NamedTemporaryFile(suffix=".pdf").name
        cls.agreement = AgreementFactory(
            partner=cls.partner,
            country_programme=CountryProgrammeFactory(wbs="random WBS"),
            attached_agreement=attachment,
            start=datetime.date.today(),
            end=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by=cls.unicef_staff,
            signed_by_partner_date=datetime.date.today()
        )
        cls.agreement.authorized_officers.add(cls.partnerstaff)
        cls.agreement.save()
        # This is here to test partner scoping
        AgreementFactory(signed_by_unicef_date=datetime.date.today())
        cls.intervention = InterventionFactory(
            agreement=cls.agreement,
            document_type='SHPD',
            status='draft',
            start=datetime.date.today(),
            end=datetime.date.today(),
            submission_date=datetime.date.today(),
            submission_date_prc=datetime.date.today(),
            review_date_prc=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            unicef_signatory=cls.unicef_staff,
            population_focus="Population focus",
            partner_authorized_officer_signatory=cls.partnerstaff,
            country_programme=cls.agreement.country_programme,
        )
        cls.ib = InterventionBudgetFactory(intervention=cls.intervention, currency="USD")
        cls.planned_visit = PartnerPlannedVisitsFactory(partner=cls.partner)

        output_res_type, _ = ResultType.objects.get_or_create(name='Output')
        cls.result = ResultFactory(result_type=output_res_type)

    def test_intervention_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/interventions/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)

        self.assertEqual(dataset._get_headers(), [
            "Partner",
            "Vendor #",
            "Status",
            "Partner Type",
            "Agreement",
            "Country Programme",
            "Document Type",
            "Reference Number",
            "Document Title",
            "Start Date",
            "End Date",
            "UNICEF Office",
            "Sections",
            "Locations",
            "Contingency PD",
            "Cluster",
            "UNICEF Focal Points",
            "CSO Authorized Officials",
            "Budget Currency",
            "Total CSO Contribution",
            "UNICEF Cash",
            "UNICEF Supply",
            "Total PD/SSFA Budget",
            "FR Number(s)",
            "FR Currency",
            "FR Posting Date",
            "FR Amount",
            "FR Actual CT",
            "Outstanding DCT",
            "Document Submission Date by CSO",
            "Submission Date to PRC",
            "Review Date by PRC",
            "Signed by Partner",
            "Signed by Partner Date",
            "Signed by UNICEF",
            "Signed by UNICEF Date",
            "Days from Submission to Signed",
            "Days from Review to Signed",
            "Total no. of amendments",
            "Last amendment date",
            "Attachment type",
            "# of attachments",
            "CP Outputs",
            "URL",
        ])

        self.assertEqual(dataset[0], (
            six.text_type(self.intervention.agreement.partner.name),
            six.text_type(self.intervention.agreement.partner.vendor_number),
            self.intervention.status,
            self.intervention.agreement.partner.partner_type,
            self.intervention.agreement.agreement_number,
            six.text_type(self.intervention.country_programme.name),
            self.intervention.document_type,
            self.intervention.number,
            six.text_type(self.intervention.title),
            '{}'.format(self.intervention.start),
            '{}'.format(self.intervention.end),
            u'',
            u'',
            u'',
            six.text_type("Yes" if self.intervention.contingency_pd else "No"),
            u'',
            u'',
            u'',
            six.text_type(self.ib.currency),
            u'{:.2f}'.format(self.intervention.total_partner_contribution),
            u'{:.2f}'.format(self.intervention.total_unicef_cash),
            u'{:.2f}'.format(self.intervention.total_in_kind_amount),
            u'{:.2f}'.format(self.intervention.total_budget),
            u', '.join([fr.fr_numbers for fr in self.intervention.frs.all()]),
            u'',
            u'',
            u'',
            u'',
            u'',
            '{}'.format(self.intervention.submission_date),
            '{}'.format(self.intervention.submission_date_prc),
            '{}'.format(self.intervention.review_date_prc),
            u'{}'.format(self.intervention.partner_authorized_officer_signatory.get_full_name()),
            '{}'.format(self.intervention.signed_by_partner_date),
            self.unicef_staff.get_full_name(),
            '{}'.format(self.intervention.signed_by_unicef_date),
            '{}'.format(self.intervention.days_from_submission_to_signed),
            '{}'.format(self.intervention.days_from_review_to_signed),
            six.text_type(self.intervention.amendments.count()),
            u'',
            six.text_type(', '.join(['{}'.format(att.type.name) for att in self.intervention.attachments.all()])),
            six.text_type(self.intervention.attachments.count()),
            u'',
            u'https://testserver/pmp/interventions/{}/details/'.format(self.intervention.id),
        ))

    def test_agreement_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/agreements/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
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
            'URL',
        ])

        # we're interested in the first agreement, so it will be last in the exported list
        exported_agreement = dataset[-1]
        self.assertEqual(exported_agreement, (
            self.agreement.agreement_number,
            six.text_type(self.agreement.status),
            six.text_type(self.agreement.partner.name),
            self.agreement.agreement_type,
            '{}'.format(self.agreement.start),
            '{}'.format(self.agreement.end),
            u'',
            '{}'.format(self.agreement.signed_by_partner_date),
            self.unicef_staff.get_full_name(),
            '{}'.format(self.agreement.signed_by_unicef_date),
            ', '.join([sm.get_full_name() for sm in self.agreement.authorized_officers.all()]),
            u'',
            u'https://testserver/pmp/agreements/{}/details/'.format(self.agreement.id),
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
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
            'URL',
            'Planned Programmatic Visits'
        ])
        deleted_flag = "Yes" if self.partner.deleted_flag else "No"
        blocked = "Yes" if self.partner.blocked else "No"

        test_option = [e for e in dataset if e[0] == self.partner.vendor_number][0]
        self.assertEqual(test_option, (
            self.partner.vendor_number,
            six.text_type(self.partner.name),
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
            u'https://testserver/pmp/partners/{}/details/'.format(self.partner.id),
            u'{} (Q1:{} Q2:{}, Q3:{}, Q4:{})'.format(
                self.planned_visit.year,
                self.planned_visit.programmatic_q1,
                self.planned_visit.programmatic_q2,
                self.planned_visit.programmatic_q3,
                self.planned_visit.programmatic_q4,
            ),
        ))
