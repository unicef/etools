from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.deletion import Collector

import celery
from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger
from tenant_schemas_celery.app import get_schema_name_from_task
from unicef_locations.auth import LocationsCartoNoAuthClient
from unicef_locations.models import CartoDBTable, Location
from unicef_notification.utils import send_notification_with_template
from unicef_vision.utils import get_vision_logger_domain_model

from etools.applications.users.models import Country
from etools.libraries.locations.helpers import create_or_update_locations, get_cartodb_locations, get_remapping

logger = get_task_logger(__name__)


@celery.current_app.task(bind=True)
def import_locations(self, carto_table_pk):
    """
    Delete all locations that are not matching* in the remap table and are not in use (referenced models).
    Deactivate all locations that are in use and are not matching* in the remap table.

    In use no Matching no => Delete
    In use yes Matching no => Deactivate
    In use yes/no Matching yes => Update

    Iterate on all the “new” locations:
    if they have match update else create
    """

    carto_table = CartoDBTable.objects.get(pk=carto_table_pk)

    # SETUP LOGGER
    country = Country.objects.get(schema_name=get_schema_name_from_task(self, dict))
    log, _ = get_vision_logger_domain_model().objects.get_or_create(
        handler_name=f'LocationsHandler (lev{carto_table.location_type.admin_level})',
        business_area_code=getattr(country, 'business_area_code', ''),
        country=country,
        details=self.__class__.__name__
    )

    try:
        sql_client = SQLClient(LocationsCartoNoAuthClient(base_url=f"https://{carto_table.domain}.carto.com/"))
        old2new, to_deactivate = get_remapping(sql_client, carto_table)
        active_locations = Location.objects.filter(is_active=True, gateway=carto_table.location_type)
        collector = Collector(using='default')
        rows = get_cartodb_locations(sql_client, carto_table)
        new_pcodes = [row[carto_table.pcode_col] for row in rows]

        with transaction.atomic():
            # Location.objects.all_locations().select_for_update().only('id')

            for location in active_locations.exclude(p_code__in=new_pcodes):
                collector.collect([location])
                if collector.dependencies or location.get_children():
                    location.name = f"{location.name} [{datetime.today().strftime('%Y-%m-%d')}]"
                    location.is_active = False
                    location.save()
                    logger.info(f'Deactivating {location}')
                else:
                    location.delete()
                    logger.info(f'Deleting {location}')

            Location.objects.filter(p_code__in=to_deactivate).update(is_active=False)
            logger.info(f'Deactivating {to_deactivate}')

            for old, new in old2new.items():
                if old != new:
                    old_location = Location.objects.get(p_code=old, is_active=True)
                    old_location.p_code = new
                    old_location.save()
                    logger.info(f'Update through remapping {old} -> {new}')

            # new locations
            new, updated, skipped, error = create_or_update_locations(rows, carto_table)

            # clean_parent_level
            qs = Location.objects.filter(gateway__admin_level=carto_table.location_type.admin_level - 1, is_active=False)
            for location in qs:
                if location.is_leaf_node():
                    location.delete()
                    logger.info(f'Deleting parent {location}')
                else:
                    children = location.get_children()
                    if not children.filter(is_active=True):
                        location.is_active = False
                        location.save()
                        logger.info(f'Deactivating parent {location}')

            log.total_records = new + updated + skipped + error
            log.total_processed = new + updated
            log.successful = True
            log.save()

    except CartoException as e:
        message = "CartoDB exception occured"
        logger.exception(message)
        log.details = e
        log.exception_message = message
    finally:
        log.save()


@celery.current_app.task
def notify_import_site_completed(carto_table_pk, user_pk):
    user = get_user_model().objects.get(pk=user_pk)
    context = {
        'table': CartoDBTable.objects.get(pk=carto_table_pk),
        'recipient': user.get_full_name(),
    }
    send_notification_with_template(
        recipients=[user.email],
        template_name='locations/import_completed',
        context=context
    )
