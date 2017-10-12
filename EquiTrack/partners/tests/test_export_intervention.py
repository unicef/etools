from __future__ import unicode_literals

import datetime
import tempfile

from django.conf import settings
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
    InterventionPlannedVisitFactory,
    InterventionResultLinkFactory,
    InterventionSectorLocationLinkFactory,
    LocationFactory,
    PartnerFactory,
    PartnerStaffFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase


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
        with tempfile.NamedTemporaryFile(
                mode="w+b",
                delete=False,
                suffix=".pdf",
                dir=settings.MEDIA_ROOT
        ) as attachment:
            agreement = AgreementFactory(
                partner=partner,
                country_programme=CountryProgrammeFactory(wbs="random WBS"),
                attached_agreement=attachment.name,
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
        self.planned_visit = InterventionPlannedVisitFactory(
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
        self.assertEqual(dataset._get_headers(), [
            'Id',
            'Status',
            'Agreement',
            'Country Programme',
            'Document Type',
            'Reference Number',
            'Document Title',
            'Start Date',
            'End Date',
            'UNICEF Office',
            'UNICEF Focal Points',
            'CSO Authorized Officials',
            'Population Focus',
            'FR Number(s)',
            'CSO Contribution',
            'CSO Contribution (Local)',
            'UNICEF Cash',
            'UNICEF Cash (Local)',
            'In Kind Amount',
            'In Kind Amount (Local)',
            'Currency',
            'Total',
            'Planned Visits',
            'Document Submission Date by CSO',
            'Submission Date to PRC',
            'Review Date by PRC',
            'Review Document by PRC',
            'Signed by Partner',
            'Signed by Partner Date',
            'Signed by UNICEF',
            'Signed by UNICEF Date',
            'Signed PD Document',
            'Attachments',
            'Created',
            'Modified',
        ])

        self.assertEqual(dataset[0], (
            u'{}'.format(self.intervention.pk),
            self.intervention.status,
            self.intervention.agreement.agreement_number,
            u'',
            self.intervention.document_type,
            self.intervention.reference_number,
            unicode(self.intervention.title),
            '{}'.format(self.intervention.start),
            '{}'.format(self.intervention.end),
            u'',
            u'',
            u'',
            self.intervention.population_focus,
            u', '.join([fr.fr_numbers for fr in self.intervention.frs.all()]),
            u'{:.2f}'.format(self.intervention.planned_budget.partner_contribution),
            u'{:.2f}'.format(self.intervention.planned_budget.partner_contribution_local),
            u'{:.2f}'.format(self.intervention.planned_budget.unicef_cash),
            u'{:.2f}'.format(self.intervention.planned_budget.unicef_cash_local),
            u'{:.2f}'.format(self.intervention.planned_budget.in_kind_amount),
            u'{:.2f}'.format(self.intervention.planned_budget.in_kind_amount_local),
            u'{}'.format(self.intervention.planned_budget.currency),
            u'{:.2f}'.format(self.intervention.planned_budget.total),
            u'Year: {}, Programmatic: 1, Spot Checks: 2, Audit: 3'.format(datetime.datetime.today().year),
            '{}'.format(self.intervention.submission_date),
            '{}'.format(self.intervention.submission_date_prc),
            '{}'.format(self.intervention.review_date_prc),
            u'',
            u'{}'.format(self.intervention.partner_authorized_officer_signatory.get_full_name()),
            '{}'.format(self.intervention.signed_by_partner_date),
            u'',
            '{}'.format(self.intervention.signed_by_unicef_date),
            u'',
            u'{}: {}'.format(self.attachment.type.name, self.attachment.attachment.url),
            u'{}'.format(self.intervention.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
            u'{}'.format(self.intervention.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
        ))


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
        self.assertEqual(dataset._get_headers(), [
            "Reference Number",
            "Number",
            "Types",
            "Description",
            "Amendment File",
            "Signed Date",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.intervention.pk),
            u"{}".format(int(self.amendment.amendment_number)),
            ",".join(self.amendment.types),
            unicode(self.amendment.other_description),
            u"http://testserver{}".format(self.amendment.signed_amendment.url),
            u"{}".format(self.amendment.signed_date),
        ))

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
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Reference Number",
            "Number",
            "Types",
            "Description",
            "Amendment File",
            "Signed Date",
            "Created",
            "Modified",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.amendment.pk),
            u"{}".format(self.intervention.number),
            u"{}".format(int(self.amendment.amendment_number)),
            ",".join(self.amendment.types),
            unicode(self.amendment.other_description),
            u"http://testserver{}".format(self.amendment.signed_amendment.url),
            u"{}".format(self.amendment.signed_date),
            u'{}'.format(self.amendment.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
            u'{}'.format(self.amendment.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ')),
        ))


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
        humanitarian_tag = "Yes" if self.link.cp_output.humanitarian_tag else "No"
        hidden = "Yes" if self.link.cp_output.hidden else "No"
        ram = "Yes" if self.link.cp_output.ram else "No"
        self.assertEqual(dataset._get_headers(), [
            "Reference Number",
            "Country Programme",
            "Result Type",
            "Section",
            "Name",
            "Code",
            "From Date",
            "To Date",
            "Parent",
            "Humanitarian Tag",
            "WBS",
            "VISION Id",
            "GIC Code",
            "GIC Name",
            "SIC Code",
            "SIC Name",
            "Activity Focus Code",
            "Activity Focus Name",
            "Hidden",
            "RAM",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.intervention.number),
            u"",
            unicode(self.link.cp_output.result_type),
            u"",
            unicode(self.link.cp_output.name),
            u"",
            u"{}".format(self.link.cp_output.from_date),
            u"{}".format(self.link.cp_output.to_date),
            u"",
            humanitarian_tag,
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            hidden,
            ram,
        ))

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
        humanitarian_tag = "Yes" if self.link.cp_output.humanitarian_tag else "No"
        hidden = "Yes" if self.link.cp_output.hidden else "No"
        ram = "Yes" if self.link.cp_output.ram else "No"
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Reference Number",
            "Country Programme",
            "Result Type",
            "Section",
            "Name",
            "Code",
            "From Date",
            "To Date",
            "Parent",
            "Humanitarian Tag",
            "WBS",
            "VISION Id",
            "GIC Code",
            "GIC Name",
            "SIC Code",
            "SIC Name",
            "Activity Focus Code",
            "Activity Focus Name",
            "Hidden",
            "RAM",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.link.pk),
            u"{}".format(self.intervention.number),
            u"",
            unicode(self.link.cp_output.result_type),
            u"",
            unicode(self.link.cp_output.name),
            u"",
            u"{}".format(self.link.cp_output.from_date),
            u"{}".format(self.link.cp_output.to_date),
            u"",
            humanitarian_tag,
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            hidden,
            ram,
        ))


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
        ram_indicator = "Yes" if self.indicator.ram_indicator else "No"
        active = "Yes" if self.indicator.active else "No"
        view_on_dashboard = "Yes" if self.indicator.view_on_dashboard else "No"
        self.assertEqual(dataset._get_headers(), [
            "Reference Number",
            "Sector",
            "Result",
            "Name",
            "Code",
            "Unit",
            "UNICEF Target",
            "Sector Target",
            "Current",
            "Sector Current",
            "Assumptions",
            "Target",
            "Baseline",
            "RAM Indicator",
            "Active",
            "View on Dashboard",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.intervention.pk),
            u"",
            u"",
            unicode(self.indicator.name),
            unicode(self.indicator.code),
            u"",
            u"",
            u"",
            u"{}".format(self.indicator.current),
            u"",
            u"",
            u"",
            u"",
            ram_indicator,
            active,
            view_on_dashboard,
        ))

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
        ram_indicator = "Yes" if self.indicator.ram_indicator else "No"
        active = "Yes" if self.indicator.active else "No"
        view_on_dashboard = "Yes" if self.indicator.view_on_dashboard else "No"
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Reference Number",
            "Sector",
            "Result",
            "Name",
            "Code",
            "Unit",
            "UNICEF Target",
            "Sector Target",
            "Current",
            "Sector Current",
            "Assumptions",
            "Target",
            "Baseline",
            "RAM Indicator",
            "Active",
            "View on Dashboard",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.indicator.pk),
            u"{}".format(self.intervention.number),
            u"",
            u"",
            unicode(self.indicator.name),
            unicode(self.indicator.code),
            u"",
            u"",
            u"",
            u"{}".format(self.indicator.current),
            u"",
            u"",
            u"",
            u"",
            ram_indicator,
            active,
            view_on_dashboard,
        ))


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
        self.assertEqual(dataset._get_headers(), [
            "Reference Number",
            "Sector",
            "Name",
            "Location Type",
            "P Code",
            "Geo Point",
            "Point",
            "Latitude",
            "Longitude",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.intervention.pk),
            u"{}".format(self.link.sector.pk),
            unicode(self.location.name),
            unicode(self.location.gateway.name),
            u"{}".format(self.location.p_code),
            u"",
            u"{}".format(self.location.point),
            u"",
            u"",
        ))

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
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Reference Number",
            "Sector",
            "Name",
            "Location Type",
            "P Code",
            "Geo Point",
            "Point",
            "Latitude",
            "Longitude",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.location.pk),
            u"{}".format(self.intervention.number),
            u"{}".format(self.link.sector.name),
            unicode(self.location.name),
            unicode(self.location.gateway.name),
            u"{}".format(self.location.p_code),
            u"",
            u"{}".format(self.location.point),
            u"",
            u"",
        ))
