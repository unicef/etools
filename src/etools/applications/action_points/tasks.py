import datetime

from django.conf import settings
from django.db import connection

from celery.utils.log import get_task_logger
from django_tenants.utils import get_public_schema_name

from etools.applications.action_points.models import ActionPoint
from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.users.models import Country
from etools.config.celery import app

logger = get_task_logger(__name__)


@app.task
def notify_overdue_action_points():
    """Send a notification to assignee of an action for each
    overdue action point (day after due date)
    """
    for country in Country.objects.exclude(name__in=[get_public_schema_name(), 'Global']).all():
        connection.set_tenant(country)
        _notify_overdue_action_points(country.name)


def _notify_overdue_action_points(country_name):
    """Implementation core of notify_overdue_action_points()"""
    logger.info(
        'Starting notify overdue action points for country {}'.format(
            country_name,
        )
    )

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    overdue_action_point_qs = ActionPoint.objects.exclude(
        status=ActionPoint.STATUS_COMPLETED
    ).filter(due_date=yesterday)
    for action_point in overdue_action_point_qs.all():
        email_context = {
            'action_point': action_point,
            'url': '{}/apd/action-points/detail/{}'.format(
                settings.HOST,
                action_point.pk,
            ),
        }
        send_notification_with_template(
            sender=action_point,
            recipients=[action_point.assigned_to.email],
            template_name="action_points/action_point/overdue",
            context=email_context
        )
