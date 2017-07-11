from __future__ import unicode_literals, print_function

import datetime
import time

from django.db import connection
from celery.utils.log import get_task_logger
from EquiTrack.celery import app, send_to_slack
from EquiTrack.utils import get_current_site
from EquiTrack.mixins import AdminURLMixin

from partners.models import PartnerOrganization, Agreement, Intervention
from funds.models import FundsReservationHeader
from partners.validation.agreements import AgreementValid
from notification.email import send_mail
from users.models import Country, User
from notification.models import Notification

logger = get_task_logger(__name__)


class every_country:
    def __enter__(self):
        for c in Country.objects.exclude(name='Global').all():
            connection.set_tenant(c)
            yield c
    def __exit__(self, type, value, traceback):
        connection.set_tenant(Country.objects.get(name='Global'))

def get_task_user():
    user = None
    try:
        user = User.objects.get(username='etools_task_admin@unicef.org')
    except LookupError as e:
        logger.error("Super user not found")
    return user


@app.task
def agreement_status_automatic_transition():
        user = get_task_user()
        with every_country() as c:
            for country in c:
                try:
                    logger.info('Starting agreement auto status transition for country {}'.format(
                        country.name
                    ))

                    signed_ended_agrs = Agreement.objects.filter(status=Agreement.SIGNED, end__gt=datetime.date.today())
                    processed = 0
                    for agr in signed_ended_agrs:
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

@app.task
def intervention_notification_signed_no_frs():
    user = get_task_user()

    with every_country() as c:
        for country in c:
            logger.info('Starting intervention signed but no FRs notifications for country {}'.format(
                country.name))
            signed_interventions = Intervention.objects.filter(document_type=Intervention.PD,
                                                               status=Intervention.SIGNED,
                                                               start__gte=datetime.date.today())
            for intervention in signed_interventions:
                if intervention.frs.count() == 0:
                    print(intervention.id)
                    unicef_focal_points = [focal_point.email for focal_point in intervention.unicef_focal_points.all()]
                    email_context = {
                        'number': intervention.__unicode__(),
                        'partner': intervention.agreement.partner.name,
                        'start_date': str(intervention.start),
                        'url': 'https://{}{}'.format(get_current_site().domain, intervention.get_admin_url())
                    }
                    notification = Notification.objects.create(
                        sender=intervention,
                        recipients=unicef_focal_points, template_name="partners/partnership/signed/frs",
                        template_data=email_context
                    )
                    notification.send_notification()


@app.task
def intervention_notification_ended_fr_outstanding():
    user = get_task_user()

    with every_country() as c:
        for country in c:
            logger.info('Starting intervention signed but no FRs notifications for country {}'.format(
                country.name))
            ended_interventions = Intervention.objects.filter(document_type=Intervention.PD, status=Intervention.ENDED)
            for intervention in ended_interventions:
                if intervention.total_frs['total_actual_amt'] != intervention.total_frs['total_frs_amt']:
                    print(intervention.id)
                    unicef_focal_points = [focal_point.email for focal_point in intervention.unicef_focal_points.all()]
                    email_context = {
                        'number': intervention.__unicode__(),
                        'partner': intervention.agreement.partner.name,
                        'start_date': str(intervention.start),
                        'url': 'https://{}{}'.format(get_current_site().domain, intervention.get_admin_url())
                    }
                    notification = Notification.objects.create(
                        sender=intervention,
                        recipients=unicef_focal_points, template_name="partners/partnership/ended/frs/outstanding",
                        template_data=email_context
                    )
                    notification.send_notification()


