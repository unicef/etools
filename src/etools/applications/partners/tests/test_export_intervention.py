import datetime

from django.urls import reverse
from django.utils import six

from rest_framework import status
from tablib.core import Dataset

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.locations.tests.factories import LocationFactory
from etools.applications.partners.tests.factories import (AgreementFactory, InterventionAmendmentFactory,
                                                          InterventionAttachmentFactory, InterventionBudgetFactory,
                                                          InterventionFactory, InterventionResultLinkFactory,
                                                          InterventionSectorLocationLinkFactory, PartnerFactory,
                                                          PartnerStaffFactory,)
from etools.applications.reports.tests.factories import CountryProgrammeFactory, IndicatorFactory
from etools.applications.users.tests.factories import UserFactory


class BaseInterventionModelExportTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        partner = PartnerFactory(
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
        partnerstaff = PartnerStaffFactory(partner=partner)
        agreement = AgreementFactory(
            partner=partner,
            country_programme=CountryProgrammeFactory(wbs="random WBS"),
            attached_agreement="fake_attachment.pdf",
            start=datetime.date.today(),
            end=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by=cls.unicef_staff,
            signed_by_partner_date=datetime.date.today()
        )
        agreement.authorized_officers.add(partnerstaff)
        agreement.save()
        AgreementFactory(signed_by_unicef_date=datetime.date.today())
        cls.intervention = InterventionFactory(
            agreement=agreement,
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
            partner_authorized_officer_signatory=partnerstaff,
            country_programme=agreement.country_programme,
        )
        cls.ib = InterventionBudgetFactory(
            intervention=cls.intervention,
            currency="USD"
        )
        cls.attachment = InterventionAttachmentFactory(
            intervention=cls.intervention,
        )


class TestInterventionModelExport(BaseInterventionModelExportTestCase):
    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-list'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-list'),
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
            '{}'.format(self.intervention.signed_by_unicef_date),
            self.unicef_staff.get_full_name(),
            '{}'.format(self.intervention.signed_by_partner_date),
            '{}'.format(self.intervention.days_from_submission_to_signed),
            '{}'.format(self.intervention.days_from_review_to_signed),
            six.text_type(self.intervention.amendments.count()),
            u'',
            six.text_type(', '.join(['{}'.format(att.type.name) for att in self.intervention.attachments.all()])),
            six.text_type(self.intervention.attachments.count()),
            u'',
            u'https://testserver/pmp/interventions/{}/details/'.format(self.intervention.id),
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 61)
        self.assertEqual(len(dataset[0]), 61)


class TestInterventionAmendmentModelExport(BaseInterventionModelExportTestCase):
    def setUp(self):
        super(TestInterventionAmendmentModelExport, self).setUp()
        self.amendment = InterventionAmendmentFactory(
            intervention=self.intervention,
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-amendments'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-amendments'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 10)
        self.assertEqual(len(dataset[0]), 10)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-amendments'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 10)
        self.assertEqual(len(dataset[0]), 10)


class TestInterventionResultModelExport(BaseInterventionModelExportTestCase):
    def setUp(self):
        super(TestInterventionResultModelExport, self).setUp()
        indicator = IndicatorFactory()
        self.link = InterventionResultLinkFactory(
            intervention=self.intervention,
        )
        self.link.ram_indicators.add(indicator)

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-results'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-results'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 42)
        self.assertEqual(len(dataset[0]), 42)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-results'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 42)
        self.assertEqual(len(dataset[0]), 42)


class TestInterventionIndicatorModelExport(BaseInterventionModelExportTestCase):
    def setUp(self):
        super(TestInterventionIndicatorModelExport, self).setUp()
        self.indicator = IndicatorFactory(
            name="Name",
            code="Code"
        )
        self.link = InterventionResultLinkFactory(
            intervention=self.intervention,
        )
        self.link.ram_indicators.add(self.indicator)

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-indicators'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-indicators'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 19)
        self.assertEqual(len(dataset[0]), 19)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-indicators'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 19)
        self.assertEqual(len(dataset[0]), 19)


class TestInterventionSectorLocationLinkModelExport(BaseInterventionModelExportTestCase):
    def setUp(self):
        super(TestInterventionSectorLocationLinkModelExport, self).setUp()
        self.location = LocationFactory(
            name="Name",
        )
        self.link = InterventionSectorLocationLinkFactory(
            intervention=self.intervention,
        )
        self.link.locations.add(self.location)

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-sector-locations'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-sector-locations'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 19)
        self.assertEqual(len(dataset[0]), 19)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-sector-locations'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 18)
        self.assertEqual(len(dataset[0]), 18)
