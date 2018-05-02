from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import datetime

from django.db import connection
from django.db.models import Q

from celery.utils.log import get_task_logger

from audit.models import Audit, Engagement
from EquiTrack.celery import app
from hact.models import AggregateHact, HactEncoder
from partners.models import PartnerOrganization
from users.models import Country

logger = get_task_logger(__name__)


@app.task
def update_hact_for_country(country_name):
    country = Country.objects.get(name=country_name)
    connection.set_tenant(country)
    logger.info('Set country {}'.format(country_name))
    for partner in PartnerOrganization.objects.filter(Q(reported_cy__gt=0) | Q(total_ct_cy__gt=0)):
        logger.debug('Updating Partner {}'.format(partner.name))
        hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values
        audits = Audit.objects.filter(partner=partner, status=Engagement.FINAL,
                                      date_of_draft_report_to_unicef__year=datetime.now().year)
        hact['outstanding_findings'] = sum([
            audit.pending_unsupported_amount for audit in audits if audit.pending_unsupported_amount])

        PartnerOrganization.programmatic_visits(partner)
        partner.hact_values = json.dumps(hact, cls=HactEncoder)
        partner.save()


@app.task
def update_hact_values():
    logger.info('Hact Freeze Task process started')
    for country in Country.objects.exclude(schema_name='public'):
        update_hact_for_country.delay(country.name)
    logger.info('Hact Freeze Task generated all tasks')


@app.task
def update_aggregate_hact_values():
    logger.info('Hact Aggregator Task process started')
    for country in Country.objects.exclude(schema_name='public'):
        connection.set_tenant(country)
        aggregate_hact, _ = AggregateHact.objects.get_or_create(year=datetime.today().year)
        try:
            aggregate_hact.update()
        except Exception:
            logger.exception(country)

    logger.info('Hact Aggregator Task process finished')
