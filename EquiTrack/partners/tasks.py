from __future__ import unicode_literals, print_function

import datetime
import time

from django.db import connection
from celery.utils.log import get_task_logger
from EquiTrack.celery import app, send_to_slack

from partners.models import PartnerOrganization, Agreement, Intervention
from partners.validation.agreements import AgreementValid
from users.models import Country, User

logger = get_task_logger(__name__)

@app.task
def agreement_status_automatic_transition(country_name=None):
    user = None
    try:
        user = User.objects.get(username='etools_task_admin@unicef.org')
    except LookupError as e:
        logger.error("Super user not found")

    countries = Country.objects.exclude(name__in=['Global'])
    if country_name is not None:
        countries = countries.filter(name=country_name)

    for country in countries:
        connection.set_tenant(country)
        try:
            logger.info('Starting agreement auto status transition for country {}'.format(
                country.name
            ))

            signed_ended_agrs = Agreement.objects.filter(status=Agreement.SIGNED, end__gt=datetime.date.today())
            processed = 0
            for agr in signed_ended_agrs:
                print(agr.id)
                new_agr = agr
                new_agr.status = Agreement.ENDED
                validator = AgreementValid(new_agr, user, agr)
                if validator.is_valid:
                    new_agr.save()
                    processed += 1
                else:
                    logger.info("Agreement ID".format(new_agr.id), validator.errors)

            logger.info("processed {} agreements".format(processed))

        except BaseException as e:
            logger.error("{} Agreement Auto Transition failed, reason: {}".format(
                country.name, e.message
            ))
