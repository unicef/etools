from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import datetime

from django.db import connection
from django.utils import six

from celery.utils.log import get_task_logger

from audit.models import Audit, Engagement
from EquiTrack.celery import app
from hact.models import AggregateHact, HactEncoder
from partners.models import PartnerOrganization
from users.models import Country

logger = get_task_logger(__name__)


@app.task
def update_hact_values():
    logger.info('Hact Freeze Task process started')
    for country in Country.objects.exclude(schema_name='public'):
        connection.set_tenant(country)
        for partner in PartnerOrganization.objects.all():
            hact = json.loads(partner.hact_values) if isinstance(
                partner.hact_values, (six.text_type, six.string_types, six.binary_type)) else partner.hact_values
            audits = Audit.objects.filter(partner=partner, status=Engagement.FINAL,
                                          date_of_draft_report_to_unicef__year=datetime.now().year)
            hact['outstanding_findings'] = sum([
                audit.pending_unsupported_amount for audit in audits if audit.pending_unsupported_amount])

            partner.programmatic_visits()
            partner.hact_values = json.dumps(hact, cls=HactEncoder)
            partner.save()
    logger.info('Hact Freeze Task process finished')


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
