import datetime

from django.urls import reverse

from rest_framework import status
from tablib.core import Dataset

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.locations.tests.factories import LocationFactory
from etools.applications.partners.tests.factories import (
    AgreementFactory, InterventionAmendmentFactory, InterventionAttachmentFactory, InterventionBudgetFactory,
    InterventionFactory, InterventionResultLinkFactory, InterventionSectorLocationLinkFactory,
    PartnerFactory, PartnerStaffFactory,)
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory, IndicatorFactory, ResultFactory, SectorFactory,)
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
            "Vendor Number",
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
            str(self.intervention.agreement.partner.name),
            str(self.intervention.agreement.partner.vendor_number),
            self.intervention.status,
            self.intervention.agreement.partner.partner_type,
            self.intervention.agreement.agreement_number,
            str(self.intervention.country_programme.name),
            self.intervention.document_type,
            self.intervention.number,
            str(self.intervention.title),
            '{}'.format(self.intervention.start),
            '{}'.format(self.intervention.end),
            u'',
            u'',
            u'',
            str("Yes" if self.intervention.contingency_pd else "No"),
            u'',
            u'',
            u'',
            str(self.ib.currency),
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
            str(self.intervention.amendments.count()),
            u'',
            str(', '.join(['{}'.format(att.type.name) for att in self.intervention.attachments.all()])),
            str(self.intervention.attachments.count()),
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


class TestInterventionLocationExport(BaseInterventionModelExportTestCase):
    """
    API to export a list of interventions, and for each one, iterate
    over its locations and sections to provide a row for each
    location/section combination for each intervention.

    """
    def test_intervention_location_export(self):
        # First intervention was already created for us in setUpTestData
        partner_name = self.intervention.agreement.partner.name
        partner_vendor_code = self.intervention.agreement.partner.vendor_number

        # Assign known dates that we can test for in the output later on
        self.intervention.start = datetime.date(2013, 1, 6)
        self.intervention.end = datetime.date(2013, 3, 20)
        self.intervention.save()

        # Some locations
        self.intervention.flat_locations.add(LocationFactory(name='Location 0'), LocationFactory(name='Location 1'))

        # Some sections
        sec = SectorFactory(name='Sector 0')
        sec1 = SectorFactory(name='Sector 1')
        self.intervention.sections.add(sec, sec1)

        # Some focal points
        self.intervention.unicef_focal_points.add(
            UserFactory(first_name='Jack', last_name='Bennie'),
            UserFactory(first_name='Phil', last_name='Silver')
        )

        # Some results
        InterventionResultLinkFactory(cp_output=ResultFactory(sector=sec1, name='Result A'),
                                      intervention=self.intervention)
        InterventionResultLinkFactory(cp_output=ResultFactory(sector=sec1, name='Result B'),
                                      intervention=self.intervention)

        # Another intervention, with no locations
        self.intervention2 = InterventionFactory(
            agreement=AgreementFactory(partner=PartnerFactory(name='Partner 2', vendor_number='123')))
        # Sections
        sec2 = SectorFactory(name='Sector 2')
        sec3 = SectorFactory(name='Sector 3')
        self.intervention2.sections.add(sec2, sec3)
        # Results
        InterventionResultLinkFactory(
            cp_output=ResultFactory(sector=sec2, name='Result C'), intervention=self.intervention2)
        InterventionResultLinkFactory(
            cp_output=ResultFactory(sector=sec3, name='Result D'), intervention=self.intervention2)

        # Intervention with no sectors
        self.intervention3 = InterventionFactory(
            agreement=AgreementFactory(partner=PartnerFactory(name='Partner 3', vendor_number='456')))
        self.intervention3.flat_locations.add(LocationFactory(name='Location 2'))
        InterventionResultLinkFactory(intervention=self.intervention3, cp_output=ResultFactory(name='Result Fred'))

        self.url = reverse(
            'partners_api:intervention-locations-list',
        )

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"format": "csv"},
        )
        self.assertEqual(200, response.status_code, msg=response.content.decode('utf-8'))
        result = response.content.decode('utf-8')

        today = '{:%Y_%m_%d}'.format(datetime.date.today())
        self.assertEqual(
            f'attachment;filename=PD_locations_as_of_{today}_TST.csv',
            response['Content-Disposition'],
        )

        # Leave this here to easily uncomment for debugging.
        # print("RESULT:")
        # for line in result.split('\r\n'):
        #     print('f' + repr(line + '\r\n'))

        agreement_number_1 = self.intervention.agreement.agreement_number
        agreement_number_2 = self.intervention2.agreement.agreement_number
        agreement_number_3 = self.intervention3.agreement.agreement_number
        self.assertEqual(
            f'Partner,Vendor Number,PD Ref Number,Agreement,Status,Location,Section,CP output,Start Date,End Date,Name of UNICEF Focal Point,Hyperlink\r\n'
            f'{partner_name},{partner_vendor_code},{self.intervention.number},{agreement_number_1},draft,Location 0,Sector 0,"Result A, Result B",2013-01-06,2013-03-20,"Jack Bennie, Phil Silver",https://testserver/pmp/interventions/{self.intervention.id}/details/\r\n'
            f'{partner_name},{partner_vendor_code},{self.intervention.number},{agreement_number_1},draft,Location 1,Sector 0,"Result A, Result B",2013-01-06,2013-03-20,"Jack Bennie, Phil Silver",https://testserver/pmp/interventions/{self.intervention.id}/details/\r\n'
            f'{partner_name},{partner_vendor_code},{self.intervention.number},{agreement_number_1},draft,Location 0,Sector 1,"Result A, Result B",2013-01-06,2013-03-20,"Jack Bennie, Phil Silver",https://testserver/pmp/interventions/{self.intervention.id}/details/\r\n'
            f'{partner_name},{partner_vendor_code},{self.intervention.number},{agreement_number_1},draft,Location 1,Sector 1,"Result A, Result B",2013-01-06,2013-03-20,"Jack Bennie, Phil Silver",https://testserver/pmp/interventions/{self.intervention.id}/details/\r\n'
            f'Partner 2,123,{self.intervention2.number},{agreement_number_2},draft,,Sector 2,"Result C, Result D",,,,https://testserver/pmp/interventions/{self.intervention2.id}/details/\r\n'
            f'Partner 2,123,{self.intervention2.number},{agreement_number_2},draft,,Sector 3,"Result C, Result D",,,,https://testserver/pmp/interventions/{self.intervention2.id}/details/\r\n'
            f'Partner 3,456,{self.intervention3.number},{agreement_number_3},draft,Location 2,,Result Fred,,,,https://testserver/pmp/interventions/{self.intervention3.id}/details/\r\n',
            result,
        )
