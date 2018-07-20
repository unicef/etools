import logging

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from etools.applications.EquiTrack.util_scripts import set_country
from etools.applications.action_points import models
from etools.applications.t2f.models import ActionPoint as OldActionPoint
from etools.applications.users.models import Country

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Usage: manage.py migrate_ap
    python manage.py migrate_ap --schema <schema_name>

    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema', dest='schema', required=False,
            help='schema',
        )

    @atomic
    def handle(self, *args, **options):
        schema = options['schema']

        countries = Country.objects.all()
        if schema:
            countries = countries.filter(schema_name=schema)
        for country in countries:
            logger.info(f'Update Action Points for{country.schema_name}')
            set_country(country)
            ct = ContentType.objects.get(app_label='t2f', model='actionpoint')
            site = Site.objects.first()

            status_mapping = {
                'open': 'open',
                'ongoing': 'open',
                'completed': 'completed',
            }

            for action_point in OldActionPoint.objects.all():
                for activity in action_point.travel.activities.all():
                    if action_point.status != 'cancelled' and action_point.status:

                        ap_dict = {
                            'description': action_point.description,
                            'due_date': action_point.due_date,
                            'assigned_to': action_point.person_responsible,
                            'status': status_mapping[action_point.status],
                            'date_of_completion': action_point.completed_at,
                            'created': action_point.created_at,
                            'assigned_by': action_point.assigned_by,
                            'author': action_point.assigned_by,
                            'travel_activity': activity,
                            'partner': activity.partner,
                            'cp_output': activity.result,
                            'intervention': activity.partnership,
                        }
                        ap = models.ActionPoint.objects.create(**ap_dict)
                        comment = '{} {}'.format(action_point.action_point_number, action_point.actions_taken).strip()
                        ap.comments.create(comment=comment, content_type=ct, site=site)
                        if action_point.comments:
                            ap.comments.create(comment=action_point.comments, content_type=ct, site=site)
