from __future__ import unicode_literals
import datetime
import itertools

from django.conf import settings
from django.db import connection
from django.db.models import F, Sum

from celery.utils.log import get_task_logger

from EquiTrack.celery import app
from partners.models import Agreement, Intervention
from partners.validation.agreements import AgreementValid
from partners.validation.interventions import InterventionValid
from users.models import Country, User
from notification.models import Notification

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
                raise

    return wrapper


#@task_decorator
@app.task
def agreement_status_automatic_transition(admin=None, workspace=None, **kwargs):
    '''Check validity and save changed status (if any) for agreements that meet all of the following criteria --
        - signed
        - end date is after today
        - type != SSFA
    '''
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _make_agreement_status_automatic_transitions(country.name)


def _make_agreement_status_automatic_transitions(country_name):
    '''Implementation core of agreement_status_automatic_transition() (q.v.)'''
    logger.info('Starting agreement auto status transition for country {}'.format(country_name))

    admin_user = User.objects.get(username=settings.TASK_ADMIN_USER)

    # these are agreements that are not even valid within their own status
    # compiling a list of them to send to an admin or save somewhere in the future
    bad_agreements = []

    # SSFAs don't transition automatically unless they transition based on the intervention.
    signed_ended_agrs = Agreement.objects.filter(status=Agreement.SIGNED, end__gt=datetime.date.today())\
        .exclude(agreement_type=Agreement.SSFA)
    processed = 0

    for agr in signed_ended_agrs:
        old_status = agr.status
        # this function mutates agreement
        validator = AgreementValid(agr, user=admin_user, disable_rigid_check=True)
        if validator.is_valid:
            if agr.status != old_status:
                # this one transitioned forward
                agr.save()
                processed += 1
        else:
            bad_agreements.append(agr)

    logger.error('Bad agreements {}'.format(len(bad_agreements)))
    logger.error('Bad agreements ids: ' + ' '.join(str(a.id) for a in bad_agreements))
    logger.info('Total agreements {}'.format(signed_ended_agrs.count()))
    logger.info("Transitioned agreements {} ".format(processed))


#@task_decorator
@app.task
def intervention_status_automatic_transition(admin=None, workspace=None, **kwargs):
    '''Check validity and save changed status (if any) for interventions that meet all of the following criteria --
        - active
        - end date is yesterday

    Also for interventions that meet all of the following criteria --
        - ended
        - total outstanding_amt == 0
        - total_amt == actual_amt
    '''
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _make_intervention_status_automatic_transitions(country.name)


def _make_intervention_status_automatic_transitions(country_name):
    '''Implementation core of intervention_status_automatic_transition() (q.v.)'''
    if True:
        logger.info('Starting intervention auto status transition for country {}'.format(country_name))

        admin_user = User.objects.get(username=settings.TASK_ADMIN_USER)

        # these are agreements that are not even valid within their own status
        # compiling a list of them to send to an admin or save somewhere in the future
        bad_interventions = []

        active_ended = Intervention.objects.filter(status=Intervention.ACTIVE,
                                                   end=datetime.date.today() - datetime.timedelta(days=1))

        # get all the interventions for which their status is endend and total otustanding_amt is 0 and
        # actual_amt is the same as the total_amt

        qs = Intervention.objects\
            .prefetch_related('frs')\
            .filter(status=Intervention.ENDED)\
            .annotate(frs_total_outstanding=Sum('frs__outstanding_amt'),
                      frs_total_actual_amt=Sum('frs__actual_amt'),
                      frs_total_amt=Sum('frs__total_amt'))\
            .filter(frs_total_outstanding=0, frs_total_actual_amt=F('frs_total_amt'))

        processed = 0

        for intervention in itertools.chain(active_ended, qs):
            old_status = intervention.status

            # this function mutates the intervention
            validator = InterventionValid(intervention, user=admin_user, disable_rigid_check=True)
            if validator.is_valid:
                if intervention.status != old_status:
                    # this one transitioned forward
                    intervention.save()
                    processed += 1
            else:
                bad_interventions.append(intervention)

        logger.error('Bad interventions {}'.format(len(bad_interventions)))
        logger.error('Bad interventions ids: ' + ' '.join(a.id for a in bad_interventions))
        logger.info('Total interventions {}'.format(active_ended.count() + qs.count()))
        logger.info("Transitioned interventions {} ".format(processed))


#@task_decorator
@app.task
def intervention_notification_signed_no_frs(admin=None, workspace=None, **kwargs):
    '''This should only run once a week'''
    logger.info('Starting intervention signed but no FRs notifications for country {}'.format(workspace.name))

    signed_interventions = Intervention.objects.filter(status=Intervention.SIGNED,
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


#@task_decorator
@app.task
def intervention_notification_ended_fr_outstanding(admin=None, workspace=None, **kwargs):
    '''This will run every 2 weeks'''
    logger.info('Starting intervention signed but FRs Amount and actual '
                'do not match notifications for country {}'.format(workspace.name))

    ended_interventions = Intervention.objects.filter(status=Intervention.ENDED)
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


#@task_decorator
@app.task
def intervention_notification_ending(admin=None, workspace=None, **kwargs):
    '''This will run every 24 hours'''
    qs_results = {}

    logger.info('Starting interventions almost ending notifications for country {}'.format(workspace.name))

    qs_results["30"] = Intervention.objects.filter(
        status=Intervention.ACTIVE,
        end=datetime.datetime.today()+datetime.timedelta(days=30)
    ).prefetch_related('unicef_focal_points', 'agreement', 'agreement__partner')

    qs_results["15"] = Intervention.objects.filter(
        status=Intervention.ACTIVE,
        end=datetime.datetime.today()+datetime.timedelta(days=15)
    ).prefetch_related('unicef_focal_points', 'agreement', 'agreement__partner')

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
