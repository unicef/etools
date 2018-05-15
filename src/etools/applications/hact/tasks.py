
import json
from datetime import date, datetime

from django.db import connection, transaction
from django.db.models import F, Sum
from django.utils import timezone

from celery.utils.log import get_task_logger

from etools.applications.audit.models import Audit, Engagement, SpecialAudit, SpotCheck
from etools.applications.hact.models import AggregateHact, HactEncoder
from etools.applications.partners.models import Intervention, InterventionPlannedVisits, PartnerOrganization
from etools.applications.t2f.models import Travel, TravelActivity, TravelType
from etools.applications.tpm.models import TPMVisit
from etools.applications.users.models import Country
from etools.applications.vision.exceptions import VisionException
from etools.applications.vision.models import VisionSyncLog
from etools.config.celery import app

logger = get_task_logger(__name__)


class PartnerHactSynchronizer(object):

    def __init__(self, partner) -> None:
        self.partner = partner
        super().__init__()

    def planned_visits(self):
        """Updates the hact json field for planned visits values:
        For current year sum all programmatic values of planned visits
        If partner type is Government, then default to 0 planned visits
        """
        year = date.today().year
        if self.partner.partner_type == 'Government':
            pvq1 = pvq2 = pvq3 = pvq4 = 0
        else:
            pv = InterventionPlannedVisits.objects.filter(
                intervention__agreement__partner=self.partner, year=year,
                intervention__status__in=[Intervention.ACTIVE, Intervention.CLOSED, Intervention.ENDED]
            ).aggregate(Sum('programmatic_q1'), Sum('programmatic_q2'), Sum('programmatic_q3'), Sum('programmatic_q4'))
            pvq1 = pv['programmatic_q1__sum'] or 0
            pvq2 = pv['programmatic_q2__sum'] or 0
            pvq3 = pv['programmatic_q3__sum'] or 0
            pvq4 = pv['programmatic_q4__sum'] or 0

        hact = json.loads(self.partner.hact_values) if isinstance(
            self.partner.hact_values, str) else self.partner.hact_values
        hact['programmatic_visits']['planned']['q1'] = pvq1
        hact['programmatic_visits']['planned']['q2'] = pvq2
        hact['programmatic_visits']['planned']['q3'] = pvq3
        hact['programmatic_visits']['planned']['q4'] = pvq4
        hact['programmatic_visits']['planned']['total'] = pvq1 + pvq2 + pvq3 + pvq4
        self.partner.hact_values = hact
        self.partner.save()

    def programmatic_visits(self):
        """Updates the hact json fieldfor all completed programmatic visits"""

        pv_year = TravelActivity.objects.filter(
            travel_type=TravelType.PROGRAMME_MONITORING,
            travels__traveler=F('primary_traveler'),
            travels__status__in=[Travel.COMPLETED],
            travels__end_date__year=timezone.now().year,
            partner=self.partner,
        )

        pv = pv_year.count()
        pvq1 = pv_year.filter(travels__end_date__month__in=[1, 2, 3]).count()
        pvq2 = pv_year.filter(travels__end_date__month__in=[4, 5, 6]).count()
        pvq3 = pv_year.filter(travels__end_date__month__in=[7, 8, 9]).count()
        pvq4 = pv_year.filter(travels__end_date__month__in=[10, 11, 12]).count()

        # TPM visit are counted one per month maximum
        tpmv = TPMVisit.objects.filter(
            tpm_activities__partner=self.partner, status=TPMVisit.UNICEF_APPROVED,
            date_of_unicef_approved__year=datetime.now().year
        ).distinct()

        tpmv1 = sum([
            tpmv.filter(date_of_unicef_approved__month=1).exists(),
            tpmv.filter(date_of_unicef_approved__month=2).exists(),
            tpmv.filter(date_of_unicef_approved__month=3).exists()
        ])
        tpmv2 = sum([
            tpmv.filter(date_of_unicef_approved__month=4).exists(),
            tpmv.filter(date_of_unicef_approved__month=5).exists(),
            tpmv.filter(date_of_unicef_approved__month=6).exists()
        ])
        tpmv3 = sum([
            tpmv.filter(date_of_unicef_approved__month=7).exists(),
            tpmv.filter(date_of_unicef_approved__month=8).exists(),
            tpmv.filter(date_of_unicef_approved__month=9).exists()
        ])
        tpmv4 = sum([
            tpmv.filter(date_of_unicef_approved__month=10).exists(),
            tpmv.filter(date_of_unicef_approved__month=11).exists(),
            tpmv.filter(date_of_unicef_approved__month=12).exists()
        ])

        tpm_total = tpmv1 + tpmv2 + tpmv3 + tpmv4

        self.partner.hact_values['programmatic_visits']['completed']['q1'] = pvq1 + tpmv1
        self.partner.hact_values['programmatic_visits']['completed']['q2'] = pvq2 + tpmv2
        self.partner.hact_values['programmatic_visits']['completed']['q3'] = pvq3 + tpmv3
        self.partner.hact_values['programmatic_visits']['completed']['q4'] = pvq4 + tpmv4
        self.partner.hact_values['programmatic_visits']['completed']['total'] = pv + tpm_total

        self.partner.save()

    def spot_checks(self):
        """Updates the hact json field for all completed spot checks"""

        trip = TravelActivity.objects.filter(
            travel_type=TravelType.SPOT_CHECK,
            travels__traveler=F('primary_traveler'),
            travels__status__in=[Travel.COMPLETED],
            travels__completed_at__year=datetime.now().year,
            partner=self.partner,
        )

        trq1 = trip.filter(travels__completed_at__month__in=[1, 2, 3]).count()
        trq2 = trip.filter(travels__completed_at__month__in=[4, 5, 6]).count()
        trq3 = trip.filter(travels__completed_at__month__in=[7, 8, 9]).count()
        trq4 = trip.filter(travels__completed_at__month__in=[10, 11, 12]).count()

        audit_spot_check = SpotCheck.objects.filter(
            partner=self.partner, status=Engagement.FINAL,
            date_of_draft_report_to_unicef__year=datetime.now().year
        )

        asc1 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[1, 2, 3]).count()
        asc2 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[4, 5, 6]).count()
        asc3 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[7, 8, 9]).count()
        asc4 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[10, 11, 12]).count()

        self.partner.hact_values['spot_checks']['completed']['q1'] = trq1 + asc1
        self.partner.hact_values['spot_checks']['completed']['q2'] = trq2 + asc2
        self.partner.hact_values['spot_checks']['completed']['q3'] = trq3 + asc3
        self.partner.hact_values['spot_checks']['completed']['q4'] = trq4 + asc4

        sc = trip.count() + audit_spot_check.count()  # TODO 1.1.9c add spot checks from field monitoring
        self.partner.hact_values['spot_checks']['completed']['total'] = sc
        self.partner.save()

    def audits_completed(self):
        """Updates the hact json field for all completed audit (including special audit)"""

        audits = Audit.objects.filter(
            partner=self.partner,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef__year=datetime.now().year).count()
        s_audits = SpecialAudit.objects.filter(
            partner=self.partner,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef__year=datetime.now().year).count()
        completed_audit = audits + s_audits
        self.partner.hact_values['audits']['completed'] = completed_audit
        self.partner.save()

    def hact_properties(self):

        hact = json.loads(self.partner.hact_values) if isinstance(
            self.partner.hact_values, (str, bytes)) else self.partner.hact_values
        audits = Audit.objects.filter(partner=self.partner, status=Engagement.FINAL,
                                      date_of_draft_report_to_unicef__year=datetime.now().year)
        hact['outstanding_findings'] = sum([
            audit.pending_unsupported_amount for audit in audits if audit.pending_unsupported_amount])
        hact['assurance_coverage'] = self.partner.assurance_coverage
        self.partner.hact_values = json.dumps(hact, cls=HactEncoder)
        self.partner.save()


@app.task
def update_hact_for_country(country_name):
    country = Country.objects.get(name=country_name)
    log = VisionSyncLog(
        country=country,
        handler_name='HactSynchronizer'
    )
    connection.set_tenant(country)
    logger.info('Set country {}'.format(country_name))
    try:
        partners = PartnerOrganization.objects.active()
        for partner in partners:
            logger.debug('Updating Partner {}'.format(partner.name))
            partner_sync = PartnerHactSynchronizer(partner)
            partner_sync.programmatic_visits()
            partner_sync.planned_visits()
            partner_sync.spot_checks()
            partner_sync.audits_completed()
            partner_sync.hact_properties()
    except Exception as e:
        logger.info('HACT Sync', exc_info=True)
        log.exception_message = e
        raise VisionException
    else:
        log.total_records = partners.count()
        log.total_processed = partners.count()
        log.successful = True
    finally:
        log.save()


@app.task
def update_hact_values(*args, **kwargs):

    schema_names = kwargs.get('schema_names', [None])[0]
    logger.info('Hact Freeze Task process started')
    countries = Country.objects.exclude(schema_name='public')
    if schema_names:
        countries = countries.filter(schema_name__in=schema_names.split(','))
    for country in countries:
        update_hact_for_country.delay(country.name)
    logger.info('Hact Freeze Task generated all tasks')


@app.task
def update_aggregate_hact_values(*args, **kwargs):
    logger.info('Hact Aggregator Task process started')

    schema_names = kwargs.get('schema_names', [None])[0]
    countries = Country.objects.exclude(schema_name='public')
    if schema_names:
        countries = countries.filter(schema_name__in=schema_names.split(','))
    for country in countries:
        connection.set_tenant(country)
        with transaction.atomic():
            aggregate_hact, _ = AggregateHact.objects.get_or_create(year=datetime.today().year)
            try:
                aggregate_hact.update()
            except BaseException:
                logger.exception(country)

    logger.info('Hact Aggregator Task process finished')
