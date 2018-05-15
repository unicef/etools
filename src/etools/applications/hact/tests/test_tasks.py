from datetime import date, datetime
from mock import Mock, patch

from django.utils import timezone

from etools.applications.audit.models import Engagement
from etools.applications.audit.tests.factories import AuditFactory, SpecialAuditFactory, SpotCheckFactory
from etools.applications.hact.tasks import PartnerHactSynchronizer, update_hact_for_country
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization, PartnerType
from etools.applications.partners.tests.factories import (
    AgreementFactory, InterventionFactory, InterventionPlannedVisitsFactory, PartnerFactory,)
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.t2f.models import Travel, TravelType
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.tpm.models import TPMVisit
from etools.applications.tpm.tests.factories import TPMActivityFactory, TPMVisitFactory
from etools.applications.users.tests.factories import UserFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.hact.models import AggregateHact
from etools.applications.hact.tasks import update_aggregate_hact_values, update_hact_for_country, update_hact_values
from etools.applications.hact.tests.factories import AggregateHactFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.vision.models import VisionSyncLog


class TestAggregateHactValues(BaseTenantTestCase):
    """
    Test task which freeze global aggregated values for hact dashboard
    """

    def test_task_create(self):
        self.assertEqual(AggregateHact.objects.count(), 0)
        update_aggregate_hact_values()
        self.assertEqual(AggregateHact.objects.count(), 1)

    def test_task_update(self):
        AggregateHactFactory()
        self.assertEqual(AggregateHact.objects.count(), 1)
        update_aggregate_hact_values()
        self.assertEqual(AggregateHact.objects.count(), 1)


class TestPartnerHactSynchronizer(BaseTenantTestCase):
    def setUp(self):
        super(TestPartnerHactSynchronizer, self).setUp()
        year = date.today().year
        self.partner_organization = PartnerFactory(
            name="Partner Org 1",
            reported_cy=1000
        )
        self.cp = CountryProgrammeFactory(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=date(year - 1, 1, 1),
            to_date=date(year + 1, 1, 1),
        )
        self.pca_signed1 = AgreementFactory(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=date(year - 1, 1, 1),
            signed_by_partner_date=date(year - 1, 1, 1),
            country_programme=self.cp,
            status=Agreement.DRAFT
        )

    def test_planned_visits_gov(self):
        self.partner_organization.partner_type = PartnerType.GOVERNMENT
        self.partner_organization.save()
        intervention = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        year = date.today().year
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year,
            programmatic_q1=3
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year - 1,
            programmatic_q3=2
        )
        PartnerHactSynchronizer(self.partner_organization).planned_visits()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['planned']['total'], 0)

    def test_planned_visits_non_gov(self):
        self.partner_organization.partner_type = PartnerType.UN_AGENCY
        self.partner_organization.save()
        intervention = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        year = date.today().year
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year,
            programmatic_q1=3,
            programmatic_q4=4,
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year - 1,
            programmatic_q2=2
        )
        PartnerHactSynchronizer(self.partner_organization).planned_visits()

        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['planned']['total'], 7)

    def test_planned_visits_non_gov_no_pv_intervention(self):
        self.partner_organization.partner_type = PartnerType.UN_AGENCY
        self.partner_organization.save()
        intervention1 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        intervention2 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        year = date.today().year
        InterventionPlannedVisitsFactory(
            intervention=intervention1,
            year=year,
            programmatic_q1=1,
            programmatic_q3=3,
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention2,
            year=year - 1,
            programmatic_q4=2
        )
        PartnerHactSynchronizer(self.partner_organization).planned_visits()
        self.assertEqual(
            self.partner_organization.hact_values['programmatic_visits']['planned']['total'],
            4
        )

    def test_programmatic_visits_update_travel_activity(self):
        tz = timezone.get_default_timezone()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 0)
        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            end_date=datetime(datetime.today().year, 9, 1, tzinfo=tz)
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.PROGRAMME_MONITORING,
            partner=self.partner_organization,
        )
        PartnerHactSynchronizer(self.partner_organization).programmatic_visits()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q2'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q3'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q4'], 0)

    def test_programmatic_visits_update_tpm_visit(self):
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 0)
        visit = TPMVisitFactory(
            status=TPMVisit.UNICEF_APPROVED,
            date_of_unicef_approved=datetime(datetime.today().year, 5, 1)
        )
        visit2 = TPMVisitFactory(
            status=TPMVisit.UNICEF_APPROVED,
            date_of_unicef_approved=datetime(datetime.today().year, 5, 20)
        )
        TPMActivityFactory(
            tpm_visit=visit,
            partner=self.partner_organization,
        )
        TPMActivityFactory(
            tpm_visit=visit,
            partner=self.partner_organization,
        )
        TPMActivityFactory(
            tpm_visit=visit2,
            partner=self.partner_organization,
        )

        PartnerHactSynchronizer(self.partner_organization).programmatic_visits()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q3'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q4'], 0)

    def test_spot_checks_update_travel_activity(self):
        tz = timezone.get_default_timezone()
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 0)
        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            completed_at=datetime(datetime.today().year, 9, 1, tzinfo=tz)
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.SPOT_CHECK,
            partner=self.partner_organization,
        )

        SpotCheckFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime(datetime.today().year, 4, 1)
        )
        PartnerHactSynchronizer(self.partner_organization).spot_checks()
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 2)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q3'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q4'], 0)

    def test_audits_completed_update_travel_activity(self):
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 0)
        AuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime(datetime.today().year, 4, 1)
        )
        SpecialAuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime(datetime.today().year, 8, 1)
        )
        PartnerHactSynchronizer(self.partner_organization).audits_completed()
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 2)

    def test_update_hact_values(self):
        tz = timezone.get_default_timezone()
        year = date.today().year
        intervention1 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        intervention2 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention1,
            year=year,
            programmatic_q1=1,
            programmatic_q3=3,
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention2,
            year=year - 1,
            programmatic_q4=2
        )

        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            completed_at=datetime(datetime.today().year, 9, 1, tzinfo=tz)
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.SPOT_CHECK,
            partner=self.partner_organization,
        )

        SpotCheckFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime(datetime.today().year, 4, 1)
        )

        visit = TPMVisitFactory(
            status=TPMVisit.UNICEF_APPROVED,
            date_of_unicef_approved=datetime(datetime.today().year, 5, 1)
        )
        visit2 = TPMVisitFactory(
            status=TPMVisit.UNICEF_APPROVED,
            date_of_unicef_approved=datetime(datetime.today().year, 5, 20)
        )
        TPMActivityFactory(
            tpm_visit=visit,
            partner=self.partner_organization,
        )
        TPMActivityFactory(
            tpm_visit=visit,
            partner=self.partner_organization,
        )
        TPMActivityFactory(
            tpm_visit=visit2,
            partner=self.partner_organization,
        )

        AuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime(datetime.today().year, 4, 1)
        )
        SpecialAuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime(datetime.today().year, 8, 1)
        )

        update_hact_for_country(self.tenant.name)
        partner = PartnerOrganization.objects.get(pk=self.partner_organization.pk)
        self.assertEqual(partner.hact_values['programmatic_visits']['planned']['total'], 4)
        self.assertEqual(partner.hact_values['programmatic_visits']['planned']['q1'], 1)
        self.assertEqual(partner.hact_values['programmatic_visits']['planned']['q2'], 0)
        self.assertEqual(partner.hact_values['programmatic_visits']['planned']['q3'], 3)
        self.assertEqual(partner.hact_values['programmatic_visits']['planned']['q4'], 0)

        self.assertEqual(partner.hact_values['programmatic_visits']['completed']['total'], 1)
        self.assertEqual(partner.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(partner.hact_values['programmatic_visits']['completed']['q2'], 1)
        self.assertEqual(partner.hact_values['programmatic_visits']['completed']['q3'], 0)
        self.assertEqual(partner.hact_values['programmatic_visits']['completed']['q4'], 0)
        #
        self.assertEqual(partner.hact_values['spot_checks']['completed']['total'], 2)
        self.assertEqual(partner.hact_values['spot_checks']['completed']['q1'], 0)
        self.assertEqual(partner.hact_values['spot_checks']['completed']['q2'], 1)
        self.assertEqual(partner.hact_values['spot_checks']['completed']['q3'], 1)
        self.assertEqual(partner.hact_values['spot_checks']['completed']['q4'], 0)

        self.assertEqual(partner.hact_values['audits']['completed'], 2)

        
class TestHactForCountry(BaseTenantTestCase):

    def test_task_create(self):
        logs = VisionSyncLog.objects.all()
        self.assertEqual(logs.count(), 0)
        PartnerFactory(name="Partner XYZ", reported_cy=20000)
        update_hact_for_country(self.tenant.name)
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.total_records, 1)
        self.assertEqual(log.total_processed, 1)
        self.assertTrue(log.successful)


class TestUpdateHactValues(BaseTenantTestCase):

    def test_update_hact_values(self):
        mock_send = Mock()
        with patch("etools.applications.hact.tasks.update_hact_for_country.delay", mock_send):
            update_hact_values()
        self.assertEqual(mock_send.call_count, 1)
