from datetime import datetime

from etools.applications.audit.models import Audit, Engagement
from etools.applications.audit.tests.factories import (
    AuditFactory,
    MicroAssessmentFactory,
    RiskFactory,
    SpecialAuditFactory,
    SpotCheckFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.hact.tests.factories import AggregateHactFactory
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.tests.factories import PartnerFactory, PlannedEngagementFactory


class TestAggregateHact(BaseTenantTestCase):
    """
    Test for model
    """

    @classmethod
    def setUpTestData(cls):
        cls.aggregate_hact = AggregateHactFactory()
        cls.partner = PartnerFactory(
            organization=OrganizationFactory(
                name="Partner Name",
                organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION
            ),
            shared_with=[PartnerOrganization.AGENCY_CHOICES.UN],
            rating=PartnerOrganization.RATING_LOW,
            highest_risk_rating_name=PartnerOrganization.RATING_HIGH,
            total_ct_cp=200.0,
            total_ct_cy=400.0,
            net_ct_cy=110000.0,
            reported_cy=300.0,
            total_ct_ytd=140000.0,
        )
        cls.partner2 = PartnerFactory(
            organization=OrganizationFactory(
                name="Partner Name",
                organization_type=OrganizationType.GOVERNMENT
            ),
            shared_with=[PartnerOrganization.AGENCY_CHOICES.UNHCR],
            rating=PartnerOrganization.RATING_HIGH,
            highest_risk_rating_name=PartnerOrganization.RATING_LOW,
            total_ct_cp=200.0,
            total_ct_cy=2200.0,
            net_ct_cy=510000.0,
            reported_cy=52000.0,
            total_ct_ytd=550000.0,
        )
        PlannedEngagementFactory(partner=cls.partner, spot_check_follow_up=3)
        PlannedEngagementFactory(partner=cls.partner2, spot_check_follow_up=2)

        AuditFactory(
            status=Engagement.FINAL,
            audit_opinion=Audit.OPTION_UNQUALIFIED,
            date_of_draft_report_to_ip=datetime(datetime.today().year, 1, 3),
            additional_supporting_documentation_provided=1000.0,
            justification_provided_and_accepted=20000.0,
            write_off_required=30000.0,
            amount_refunded=400000.0,
            audited_expenditure=50.0,
            financial_findings=999.0,
            partner__reported_cy=550000.0,
        )

        AuditFactory(
            status=Engagement.FINAL,
            audit_opinion=Audit.OPTION_UNQUALIFIED,
            date_of_draft_report_to_ip=datetime(datetime.today().year - 1, 1, 3),
            additional_supporting_documentation_provided=10.0,
            justification_provided_and_accepted=20.0,
            write_off_required=30.0,
            amount_refunded=40.0,
            audited_expenditure=50.0,
            financial_findings=100.0,
            partner__reported_cy=550000.0,
        )

    def test_cash_transfers_amounts(self):
        cash_transfers_amounts = self.aggregate_hact.cash_transfers_amounts()
        self.assertEqual(len(cash_transfers_amounts), 6)
        self.assertEqual(cash_transfers_amounts[3][5], self.partner.total_ct_ytd)
        self.assertEqual(cash_transfers_amounts[3][6], 1)
        self.assertEqual(cash_transfers_amounts[5][2], self.partner2.total_ct_ytd)
        self.assertEqual(cash_transfers_amounts[5][6], 1)

    def test_get_cash_transfer_risk_rating(self):
        cash_transfer_risk_rating = self.aggregate_hact.get_cash_transfer_risk_rating()
        self.assertEqual(len(cash_transfer_risk_rating), 6)
        self.assertEqual(cash_transfer_risk_rating[2][1], self.partner2.total_ct_ytd)
        self.assertEqual(cash_transfer_risk_rating[2][3], 1)
        self.assertEqual(cash_transfer_risk_rating[5][1], self.partner.total_ct_ytd)
        self.assertEqual(cash_transfer_risk_rating[5][3], 1)

    def test_get_cash_transfer_partner_type(self):
        cash_transfer_partner_type = self.aggregate_hact.get_cash_transfer_partner_type()
        self.assertEqual(len(cash_transfer_partner_type), 3)
        self.assertEqual(cash_transfer_partner_type[1], ['CSO', self.partner.total_ct_ytd, '#FECC02', 1])
        self.assertEqual(cash_transfer_partner_type[2], ['GOV', self.partner2.total_ct_ytd, '#F05656', 1])

    def test_get_spot_checks_completed(self):
        SpotCheckFactory(
            partner__reported_cy=550000.0, status=Engagement.FINAL, date_of_draft_report_to_ip=datetime(datetime.today().year, 12, 5))
        SpotCheckFactory(
            partner__reported_cy=550000.0, status=Engagement.FINAL, date_of_draft_report_to_ip=datetime(datetime.today().year - 1, 12, 5))
        SpotCheckFactory(
            partner__reported_cy=550000.0, status=Engagement.FINAL,
            date_of_draft_report_to_ip=datetime(datetime.today().year, 6, 3),
            agreement__auditor_firm__unicef_users_allowed=True)
        SpotCheckFactory(
            status=Engagement.REPORT_SUBMITTED, date_of_draft_report_to_ip=datetime(datetime.today().year - 1, 2, 1))

        spot_checks_completed = self.aggregate_hact.get_spot_checks_completed()
        self.assertEqual(len(spot_checks_completed), 3)
        self.assertEqual(spot_checks_completed[1], ['Staff', 1])
        self.assertEqual(spot_checks_completed[2], ['Service Providers', 1])

    def test_get_assurance_activities(self):
        SpecialAuditFactory(
            partner__reported_cy=550000.0, status=Engagement.FINAL,
            date_of_draft_report_to_ip=datetime(datetime.today().year, 2, 3))
        SpecialAuditFactory(
            partner__reported_cy=550000.0, status=Engagement.FINAL,
            date_of_draft_report_to_ip=datetime(datetime.today().year - 1, 2, 3))
        MicroAssessmentFactory(
            partner__reported_cy=550000.0, status=Engagement.FINAL,
            date_of_draft_report_to_ip=datetime(datetime.today().year, 8, 10))
        assurance_activities = self.aggregate_hact.get_assurance_activities()
        self.assertEqual(len(list(assurance_activities.keys())), 6)
        self.assertEqual(assurance_activities['programmatic_visits']['completed'], 0)
        self.assertEqual(assurance_activities['programmatic_visits']['min_required'], 5)
        self.assertEqual(assurance_activities['spot_checks']['completed'], 0)
        self.assertEqual(assurance_activities['spot_checks']['required'], 6)
        self.assertEqual(assurance_activities['scheduled_audit'], 1)
        self.assertEqual(assurance_activities['special_audit'], 1)
        self.assertEqual(assurance_activities['micro_assessment'], 1)

    def test_get_financial_findings(self):

        def _check_item(financial_dict_item, name, value, highlighted):
            self.assertEqual(financial_dict_item['name'], name)
            self.assertEqual(financial_dict_item['value'], value)
            self.assertEqual(financial_dict_item['highlighted'], highlighted)

        financial_findings = self.aggregate_hact.get_financial_findings()
        self.assertEqual(len(financial_findings), 8)
        _check_item(financial_findings[0], 'Total Audited Expenditure', 50.0, False)
        _check_item(financial_findings[1], 'Total Financial Findings', 999.0, True)
        _check_item(financial_findings[2], 'Refunds', 400000.0, False)
        _check_item(financial_findings[3], 'Additional Supporting Documentation Received', 1000.0, False)
        _check_item(financial_findings[4], 'Justification Provided and Accepted', 20000.0, False)
        _check_item(financial_findings[5], 'Impairment', 30000.0, False)
        _check_item(financial_findings[6], 'Outstanding current year (Requires Follow-up)', -430001.0, True)
        _check_item(financial_findings[7], 'Outstanding prior year', 20.0, True)

    def test_get_financial_findings_numbers(self):

        def _check_item(financial_dict_item, name, value):
            self.assertEqual(financial_dict_item['name'], name)
            self.assertEqual(financial_dict_item['value'], value)

        RiskFactory(
            value=4,
            engagement=AuditFactory(
                partner__reported_cy=550000.0,
                status=Engagement.FINAL,
                audit_opinion=Audit.OPTION_QUALIFIED,
                date_of_draft_report_to_ip=datetime(datetime.today().year, 1, 3),
            )
        )
        RiskFactory(
            value=2,
            engagement=AuditFactory(
                partner__reported_cy=550000.0,
                status=Engagement.REPORT_SUBMITTED,
                audit_opinion=Audit.OPTION_ADVERSE,
                date_of_draft_report_to_ip=datetime(datetime.today().year - 1, 4, 7),
            )
        )
        RiskFactory(
            value=1,
            engagement=AuditFactory(
                partner__reported_cy=550000.0,
                status=Engagement.PARTNER_CONTACTED,
                audit_opinion=Audit.OPTION_DENIAL,
                date_of_draft_report_to_ip=datetime(datetime.today().year - 1, 4, 7),
            )
        )

        financial_findings_numbers = self.aggregate_hact.get_financial_findings_numbers()
        self.assertEqual(len(financial_findings_numbers), 4)

        _check_item(financial_findings_numbers[0], 'Number of High Priority Findings', 1)
        _check_item(financial_findings_numbers[1], 'Number of Medium Priority Findings', 0)
        _check_item(financial_findings_numbers[2], 'Number of Low Priority Findings', 0)

        self.assertEqual(len(financial_findings_numbers[3]['value']), 4)
        _check_item(financial_findings_numbers[3]['value'][0], 'qualified', 1)
        _check_item(financial_findings_numbers[3]['value'][1], 'unqualified', 1)
        _check_item(financial_findings_numbers[3]['value'][2], 'denial', 0)
        _check_item(financial_findings_numbers[3]['value'][3], 'adverse', 0)
