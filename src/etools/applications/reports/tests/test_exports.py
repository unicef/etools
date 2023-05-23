import datetime

from django.urls import reverse

from rest_framework import status
from tablib import Dataset
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.reports.tests.factories import AppliedIndicatorFactory, CountryProgrammeFactory
from etools.applications.users.tests.factories import UserFactory


class TestInterventionAppliedIndicatorsV2Export(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                organization_type=OrganizationType.GOVERNMENT,
                vendor_number='Vendor No',
                short_name="Short Name",
            ),
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
        cls.agreement = AgreementFactory(
            partner=cls.partner,
            country_programme=CountryProgrammeFactory(wbs="random WBS"),
            attached_agreement="fake_attachment.pdf",
            start=datetime.date.today(),
            end=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by=cls.unicef_staff,
            signed_by_partner_date=datetime.date.today()
        )
        cls.intervention = InterventionFactory(
            agreement=cls.agreement,
            document_type=Intervention.SPD,
            status=Intervention.DRAFT,
            start=datetime.date.today(),
            end=datetime.date.today(),
            submission_date=datetime.date.today(),
            submission_date_prc=datetime.date.today(),
            review_date_prc=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            unicef_signatory=cls.unicef_staff,
            population_focus="Population focus",
            country_programme=cls.agreement.country_programme,
            cfei_number='cfei',
        )
        cls.indicator = AppliedIndicatorFactory(
            lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention)
        )
        cls.indicator.locations.add(LocationFactory())

    def test_csv_export(self):
        response = self.forced_auth_req(
            'get',
            reverse('reports:intervention-applied-indicator'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            'Partner Name',
            'Vendor Number',
            'Vendor',
            'PD / SSFA status',
            'PD / SSFA start date',
            'PD / SSFA end date',
            'Country Programme',
            'PD / SSFA ref',
            'Locations',
            'CP Output',
            'Lower Result',
            'Indicator',
            'Section',
            'Cluster Name',
            'Indicator Unit',
            'Indicator Type',
            'Baseline Numerator',
            'Baseline Denominator',
            'Target Numerator',
            'Target Denominator',
            'Means of verification',
            'RAM indicators',
            'Location',
            'UNPP Number',
        ])

        self.assertEqual(dataset[0], (
            self.intervention.agreement.partner.name,
            'Vendor No',
            '',
            'Development',
            '{}'.format(self.intervention.start),
            '{}'.format(self.intervention.end),
            str(self.intervention.agreement.country_programme),
            self.intervention.reference_number,
            '',
            str(self.indicator.lower_result.result_link.cp_output),
            self.indicator.lower_result.name,
            str(self.indicator.indicator),
            '',
            '',
            'number',
            '-',
            str(self.indicator.baseline['v']),
            '-',
            str(self.indicator.target['v']),
            '-',
            '',
            '',
            ','.join([location.name for location in self.indicator.locations.all()]),
            'cfei',
        ))
