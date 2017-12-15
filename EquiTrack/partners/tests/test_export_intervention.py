from __future__ import unicode_literals

import datetime

from django.core.urlresolvers import reverse
from rest_framework import status
from tablib.core import Dataset

from EquiTrack.factories import (
    AgreementFactory,
    CountryProgrammeFactory,
    CurrencyFactory,
    IndicatorFactory,
    InterventionFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionBudgetFactory,
    InterventionPlannedVisitsFactory,
    InterventionResultLinkFactory,
    InterventionSectorLocationLinkFactory,
    PartnerFactory,
    PartnerStaffFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase
from locations.tests.factories import LocationFactory


class BaseInterventionModelExportTestCase(APITenantTestCase):
    def setUp(self):
        super(BaseInterventionModelExportTestCase, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
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
            signed_by=self.unicef_staff,
            signed_by_partner_date=datetime.date.today()
        )
        agreement.authorized_officers.add(partnerstaff)
        agreement.save()
        AgreementFactory(signed_by_unicef_date=datetime.date.today())
        self.intervention = InterventionFactory(
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
            unicef_signatory=self.unicef_staff,
            population_focus="Population focus",
            partner_authorized_officer_signatory=partnerstaff,
        )
        self.ib = InterventionBudgetFactory(
            intervention=self.intervention,
            currency=CurrencyFactory()
        )
        self.planned_visit = InterventionPlannedVisitsFactory(
            intervention=self.intervention,
        )
        self.attachment = InterventionAttachmentFactory(
            intervention=self.intervention,
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
            'CP Outputs',
            'RAM Indicators',
            'FR Number(s)',
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
            'URL',
            'Migration messages',
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
            u'',
            u'',
            u', '.join([fr.fr_numbers for fr in self.intervention.frs.all()]),
            u'{:.2f}'.format(self.intervention.total_unicef_cash_local),
            u'{:.2f}'.format(self.intervention.total_unicef_budget),
            u'{:.2f}'.format(self.intervention.total_partner_contribution),
            u'{:.2f}'.format(self.intervention.total_partner_contribution_local),
            u'{} ({})'.format(self.planned_visit.programmatic, self.planned_visit.year),
            u'{} ({})'.format(self.planned_visit.spot_checks, self.planned_visit.year),
            u'{} ({})'.format(self.planned_visit.audit, self.planned_visit.year),
            '{}'.format(self.intervention.submission_date),
            '{}'.format(self.intervention.submission_date_prc),
            '{}'.format(self.intervention.review_date_prc),
            u'{}'.format(self.intervention.partner_authorized_officer_signatory.get_full_name()),
            '{}'.format(self.intervention.signed_by_unicef_date),
            u'',
            '{}'.format(self.intervention.signed_by_partner_date),
            '{}'.format(self.intervention.days_from_submission_to_signed),
            '{}'.format(self.intervention.days_from_review_to_signed),
            u'https://testserver/pmp/interventions/{}/details/'.format(self.intervention.id),
            u'',
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('partners_api:intervention-list'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 52)
        self.assertEqual(len(dataset[0]), 52)


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
        dataset = Dataset().load(response.content, 'csv')
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
        dataset = Dataset().load(response.content, 'csv')
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
        dataset = Dataset().load(response.content, 'csv')
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
        dataset = Dataset().load(response.content, 'csv')
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
        dataset = Dataset().load(response.content, 'csv')
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
        dataset = Dataset().load(response.content, 'csv')
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
        dataset = Dataset().load(response.content, 'csv')
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
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 18)
        self.assertEqual(len(dataset[0]), 18)
