from __future__ import unicode_literals, print_function

import datetime
import time

from django.db import connection
from django.db.models import F
from celery.utils.log import get_task_logger
from EquiTrack.celery import app, send_to_slack
from EquiTrack.utils import get_current_site
from EquiTrack.mixins import AdminURLMixin

from partners.models import PartnerOrganization, Agreement, Intervention
from funds.models import FundsReservationHeader
from partners.validation.agreements import AgreementValid
from partners.validation.interventions import InterventionValid
from notification.email import send_mail
from users.models import Country, User
from notification.models import Notification
from t2f.models import Travel, TravelActivity, ActionPoint

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


def get_intervention_context(i):
    return {
                'number': i.__unicode__(),
                'partner': i.agreement.partner.name,
                'start_date': str(i.start),
                'url': 'https://{}{}'.format(get_current_site().domain, i.get_admin_url()),
                'unicef_focal_points': [focal_point.email for focal_point in i.unicef_focal_points.all()],
           }


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
def intervention_status_active_automatic_transition():
        user = get_task_user()
        with every_country() as c:
            for country in c:
                try:
                    logger.info('Starting intervention auto status transition for country {}'.format(
                        country.name
                    ))

                    signed = Intervention.objects.filter(status=Intervention.SIGNED, start=datetime.date.today())
                    processed = 0
                    for i in signed:
                        if i.frs.count() > 0:
                            i.status = Intervention.ACTIVE
                            validator = InterventionValid(i, user)
                            if validator.is_valid:
                                i.save()
                                processed += 1
                            else:
                                logger.info("Intervention ID".format(i.id), validator.errors)

                    logger.info("processed {} interventions".format(processed))

                except BaseException as e:
                    logger.error("{} Intervention Auto Transition failed, reason: {}".format(
                        country.name, e.message
                    ))


@app.task
def intervention_status_ended_automatic_transition():
        user = get_task_user()
        with every_country() as c:
            for country in c:
                try:
                    logger.info('Starting intervention auto status transition for country {}'.format(
                        country.name
                    ))

                    active_ended = Intervention.objects.filter(status=Intervention.ACTIVE,
                                                               end=datetime.date.today() - datetime.timedelta(days=1))
                    processed = 0
                    for i in active_ended:
                        i.status = Intervention.ENDED
                        validator = InterventionValid(i, user)
                        if validator.is_valid:
                            i.save()
                            processed += 1
                        else:
                            logger.info("Intervention ID".format(i.id), validator.errors)

                    logger.info("processed {} interventions".format(processed))

                except BaseException as e:
                    logger.error("{} Intervention Auto Transition failed, reason: {}".format(
                        country.name, e.message
                    ))


@app.task
def intervention_status_closed_automatic_transition():
        user = get_task_user()
        with every_country() as c:
            for country in c:
                try:
                    logger.info('Starting intervention auto status transition for country {}'.format(
                        country.name
                    ))
                    funds_satisfied = FundsReservationHeader.objects.filter(outstanding_amt=0,
                                                          actual_amt=F('total_amt'),
                                                          intervention__status=Intervention.ENDED
                                                                            ).values_list('intervention_id', flat=True)

                    # TODO test this query with actual records
                    action_points_satisfied = ActionPoint.objects.filter(
                        status=ActionPoint.COMPLETED,
                        travel__activities__partnership__status=Intervention.ENDED
                    ).values_list('travel__activities__partnership', flat=True)

                    in_second_but_not_in_first = action_points_satisfied - funds_satisfied
                    interventions = funds_satisfied + list(in_second_but_not_in_first)
                    processed = 0
                    for int_id in interventions:
                        i = Intervention.objects.get(id=int_id)
                        i.status = Intervention.closed
                        validator = InterventionValid(i, user)
                        if validator.is_valid:
                            i.save()
                            processed += 1
                        else:
                            logger.info("Intervention ID".format(i.id), validator.errors)

                    logger.info("processed {} interventions".format(processed))

                except BaseException as e:
                    logger.error("{} Intervention Auto Transition failed, reason: {}".format(
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
                    email_context = get_intervention_context(intervention)
                    notification = Notification.objects.create(
                        sender=intervention,
                        recipients=email_context['unicef_focal_points'],
                        template_name="partners/partnership/signed/frs",
                        template_data=email_context
                    )
                    notification.send_notification()


@app.task
def intervention_notification_ended_fr_outstanding():
    user = get_task_user()

    with every_country() as c:
        for country in c:
            logger.info('Starting intervention signed but FRs Amount and actual '
                        'do not match notifications for country {}'.format(country.name))
            ended_interventions = Intervention.objects.filter(document_type=Intervention.PD, status=Intervention.ENDED)
            for intervention in ended_interventions:
                if intervention.total_frs['total_actual_amt'] != intervention.total_frs['total_frs_amt']:
                    print(intervention.id)
                    email_context = get_intervention_context(intervention)
                    notification = Notification.objects.create(
                        sender=intervention,
                        recipients=email_context['unicef_focal_points'], template_name="partners/partnership/ended/frs/outstanding",
                        template_data=email_context
                    )
                    notification.send_notification()


@app.task
def intervention_notification_ending():
    user = get_task_user()
    qs_results = {}
    with every_country() as c:
        for country in c:
            logger.info('Starting interventions almost ending notifications for country {}'.format(
                country.name))
            qs_results["30"] = Intervention.objects.filter(
                document_type=Intervention.PD,
                status=Intervention.ACTIVE,
                end=datetime.datetime.today()+datetime.timedelta(days=30)
            )

            qs_results["15"] = Intervention.objects.filter(
                document_type=Intervention.PD,
                status=Intervention.ACTIVE,
                end=datetime.datetime.today()+datetime.timedelta(days=15)
            )

            for k, v in qs_results.items():
                for intervention in v:
                    print(intervention.id)
                    email_context = get_intervention_context(intervention)
                    email_context["days"] = k
                    notification = Notification.objects.create(
                        sender=intervention,
                        recipients=email_context['unicef_focal_points'], template_name="partners/partnership/ending",
                        template_data=email_context
                    )
                    notification.send_notification()


