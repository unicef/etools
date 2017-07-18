from __future__ import unicode_literals, print_function

import datetime
import time

from django.conf import settings
from django.db import connection
from django.db.models import F
from celery.utils.log import get_task_logger
from EquiTrack.celery import app, send_to_slack

from partners.models import PartnerOrganization, Agreement, Intervention
from funds.models import FundsReservationHeader
from partners.validation.agreements import AgreementValid
from partners.validation.interventions import InterventionValid
from notification.email import send_mail
from users.models import Country, User
from notification.models import Notification
from t2f.models import Travel, TravelActivity, ActionPoint

logger = get_task_logger(__name__)


def get_intervention_context(i):
    return {
        'number': i.__unicode__(),
        'partner': i.agreement.partner.name,
        'start_date': str(i.start),
        'url': 'https://{}/pmp/partners/{}/details'.format(settings.HOST, i.id),
        'unicef_focal_points': [focal_point.email for focal_point in i.unicef_focal_points.all()]
    }


def task_decorator(funct):
    admin = User.objects.get(username=settings.TASK_ADMIN_USER)
    def wrapper(*args, **kwargs):
        for c in Country.objects.exclude(name='Global').all():
            connection.set_tenant(c)
            kwargs['workspace'] = c
            kwargs['admin'] = admin
            try:
                funct(*args, **kwargs)
            except BaseException:
                #cleanup
                pass

    return wrapper


@app.task
@task_decorator
def agreement_status_automatic_transition(admin=None, workspace=None, **kwargs):

        logger.info('Starting agreement auto status transition for country {}'.format(
            workspace.name
        ))

        # these are agreements that are not even valid within their own status
        # compiling a list of them to send to an admin or save somewhere in the future
        bad_agreements = []

        signed_ended_agrs = Agreement.objects.filter(status=Agreement.SIGNED, end__gt=datetime.date.today())
        processed = 0

        for agr in signed_ended_agrs:
            old_status = agr.status

            # this function mutates agreement
            validator = AgreementValid(agr, user=admin, disable_rigid_check=True)
            if validator.is_valid:
                if agr.status != old_status:
                    # this one transitioned forward
                    agr.save()
                    processed += 1
            else:
                bad_agreements.append(agr)
                logger.info("Agreement i".format(agr.id), validator.errors)

        logger.info("processed {} agreements".format(processed))


@app.task
@task_decorator
def intervention_status_automatic_transition(admin=None, workspace=None, **kwargs):

        logger.info('Starting agreement auto status transition for country {}'.format(
            workspace.name
        ))

        # these are agreements that are not even valid within their own status
        # compiling a list of them to send to an admin or save somewhere in the future
        bad_interventions = []

        active_ended = Intervention.objects.filter(status=Intervention.ACTIVE,
                                                   end=datetime.date.today() - datetime.timedelta(days=1))
        processed = 0

        for intervention in active_ended:
            old_status = intervention.status

            # this function mutates agreement
            validator = InterventionValid(intervention, user=admin, disable_rigid_check=True)
            if validator.is_valid:
                if intervention.status != old_status:
                    # this one transitioned forward
                    intervention.save()
                    processed += 1
            else:
                bad_interventions.append(intervention)
                logger.info("Intervention is not valid {}".format(intervention.id), validator.errors)

        logger.info("processed {} agreements".format(processed))


@app.task
@task_decorator
def intervention_status_closed_automatic_transition(admin=None, workspace=None, **kwargs):

        logger.info('Starting intervention auto status transition for country {}'.format(workspace.name))
        funds_satisfied = FundsReservationHeader.objects.filter(outstanding_amt=0,
                                                                actual_amt=F('total_amt'),
                                                                intervention__status=Intervention.ENDED)

        # TODO add action point query when action points will have a relationship to interventions
        bad_interventions = []
        processed = 0
        for intervention in funds_satisfied:
            intervention.status = Intervention.closed
            old_status = intervention.status

            # this function mutates agreement
            validator = InterventionValid(intervention, user=admin, disable_rigid_check=True)
            if validator.is_valid:
                if intervention.status != old_status:
                    # this one transitioned forward
                    intervention.save()
                    processed += 1
            else:
                bad_interventions.append(intervention)
                logger.info("Intervention is not valid {}".format(intervention.id), validator.errors)

        logger.info("processed {} interventions".format(processed))




@app.task
@task_decorator
def intervention_notification_signed_no_frs(admin=None, workspace=None, **kwargs):

    logger.info('Starting intervention signed but no FRs notifications for country {}'.format(workspace.name))

    signed_interventions = Intervention.objects.filter(document_type__in=[Intervention.PD, Intervention.SHPD],
                                                       status=Intervention.SIGNED,
                                                       start__gte=datetime.date.today(),
                                                       frs__isnull=True)

    for intervention in signed_interventions:
        email_context = get_intervention_context(intervention)
        notification = Notification.objects.create(
            sender=intervention,
            recipients=email_context['unicef_focal_points'],
            template_name="partners/partnership/signed/frs",
            template_data=email_context
        )
        notification.send_notification()


@app.task
@task_decorator
def intervention_notification_ended_fr_outstanding(admin=None, workspace=None, **kwargs):

    logger.info('Starting intervention signed but FRs Amount and actual '
                'do not match notifications for country {}'.format(workspace.name))

    ended_interventions = Intervention.objects.filter(document_type__in=[Intervention.PD, Intervention.SHPD],
                                                      status=Intervention.ENDED)
    for intervention in ended_interventions:
        if intervention.total_frs['total_actual_amt'] != intervention.total_frs['total_frs_amt']:
            email_context = get_intervention_context(intervention)
            notification = Notification.objects.create(
                sender=intervention,
                recipients=email_context['unicef_focal_points'],
                template_name="partners/partnership/ended/frs/outstanding",
                template_data=email_context
            )
            notification.send_notification()


@app.task
@task_decorator
def intervention_notification_ending(admin=None, workspace=None, **kwargs):

    qs_results = {}

    logger.info('Starting interventions almost ending notifications for country {}'.format(workspace.name))

    qs_results["30"] = Intervention.objects.filter(
        document_type__in=[Intervention.PD, Intervention.SHPD],
        status=Intervention.ACTIVE,
        end=datetime.datetime.today()+datetime.timedelta(days=30)
    )

    qs_results["15"] = Intervention.objects.filter(
        document_type__in=[Intervention.PD, Intervention.SHPD],
        status=Intervention.ACTIVE,
        end=datetime.datetime.today()+datetime.timedelta(days=15)
    )

    for k in qs_results:
        for intervention in qs_results[k]:
            email_context = get_intervention_context(intervention)
            email_context["days"] = k
            notification = Notification.objects.create(
                sender=intervention,
                recipients=email_context['unicef_focal_points'],
                template_name="partners/partnership/ending",
                template_data=email_context
            )
            notification.send_notification()


