import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import F, Value
from django.db.models.functions import Concat

import celery
from carto.exceptions import CartoException
from celery.utils.log import get_task_logger
from tenant_schemas_celery.app import get_schema_name_from_task
from unicef_locations.models import CartoDBTable
from unicef_locations.synchronizers import LocationSynchronizer
from unicef_locations.utils import get_location_model
from unicef_vision.utils import get_vision_logger_domain_model

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.users.models import Country
from etools.applications.utils.query import has_related_records

logger = get_task_logger(__name__)


class eToolsLocationSynchronizer(LocationSynchronizer):
    """eTools version of synchronizer with use the VisionSyncLog to store log execution"""

    def __init__(self, pk, schema) -> None:
        super().__init__(pk)
        country = Country.objects.get(schema_name=schema)
        self.log, _ = get_vision_logger_domain_model().objects.get_or_create(
            handler_name=f'LocationsHandler (lev{self.carto.admin_level})',
            business_area_code=getattr(country, 'business_area_code', ''),
            country=country,
            details=self.__class__.__name__
        )

    def sync(self):
        try:
            new, updated, skipped, error = super().sync()
            self.log.total_records = new + updated + skipped + error
            self.log.total_processed = new + updated
            self.log.successful = True
            self.log.exception_message = 'Congrats: Success'
        except CartoException as e:
            self.log.exception_message = e
            self.log.successful = False
        finally:
            self.log.save()

    def create_or_update_locations(self, batch_size=500):
        """
        Create or update locations based on p-code (only active locations are considerate)

        """
        logging.info('Create/Update new locations')
        rows = self.get_cartodb_locations()
        new, updated, skipped, error = 0, 0, 0, 0
        logging.info(f'Total Rows {len(rows)}')
        logging.info(f'Batch size {batch_size}')
        for idx, batch in enumerate(zip(*[iter(rows)] * batch_size)):
            logging.info(f'processing batch {idx+1}')
            batch = list(batch)
            indexed_batch = {item[self.carto.pcode_col]: item for item in batch}
            # first get all the pcodes intended to be updated from the rows
            all_new_pcodes = [r[self.carto.pcode_col] for r in batch]
            # get all records that exist for these pcodes that will need to be adjusted
            existing_loc_qs = get_location_model().objects.filter(p_code__in=all_new_pcodes, is_active=True)
            # from batch keep all rows that are new
            rows_to_create = [row for row in batch if row[self.carto.pcode_col]
                              not in existing_loc_qs.values_list("p_code", flat=True)]

            # get_all_parents and map them by p_code:
            parent_pcodes = []
            for row in batch:
                parent_pcode = row[self.carto.parent_code_col] if self.carto.parent_code_col in row else None
                if parent_pcode:
                    parent_pcodes.append(row[self.carto.parent_code_col])
            parents_qs = get_location_model().objects.filter(p_code__in=parent_pcodes, is_active=True)
            # parent location dict {pcode: item}
            parents = {r.p_code: r for r in parents_qs.all()}

            # make a list of tuples (row_from_carto, existing_location_object) to iterate over and update
            update_tuples = [(indexed_batch[loc.p_code], loc) for loc in existing_loc_qs.all()]
            locs_to_update = []
            for row, existing_loc in update_tuples:
                pcode = row[self.carto.pcode_col]
                name = row[self.carto.name_col]
                geom = row['the_geom']
                parent_code = row[self.carto.parent_code_col] if self.carto.parent_code_col in row else None
                if all([name, pcode, geom]):
                    geom_key = 'point' if 'Point' in geom else 'geom'
                    existing_loc.admin_level = self.carto.admin_level
                    existing_loc.admin_level_name = self.carto.admin_level_name
                    existing_loc.name = name
                    existing_loc.parent = parents.get(parent_code, None) if parent_code else None
                    setattr(existing_loc, geom_key, geom)
                    locs_to_update.append(existing_loc)
                    updated += 1
                else:
                    skipped += 1
                    logger.info(f"Skipping row pcode {pcode}")

            locs_to_create = []
            for row in rows_to_create:
                pcode = row[self.carto.pcode_col]
                name = row[self.carto.name_col]
                geom = row['the_geom']
                parent_code = row[self.carto.parent_code_col] if self.carto.parent_code_col in row else None
                geom_key = 'point' if 'Point' in geom else 'geom'
                if all([name, pcode, geom]):
                    values = {
                        'p_code': pcode,
                        'is_active': True,
                        'admin_level': self.carto.admin_level,
                        'admin_level_name': self.carto.admin_level_name,
                        'name': name,
                        geom_key: geom,
                        'parent': parents.get(parent_code, None) if parent_code else None
                    }
                    # set everything to 0 in the tree, we'll rebuild later
                    for key in ['lft', 'rght', 'level', 'tree_id']:
                        values[key] = 0
                    new_rec = get_location_model()(**values)
                    locs_to_create.append(new_rec)
                    new += 1
                else:
                    skipped += 1
                    logger.info(f"Skipping row pcode {pcode}")

            # update the records:
            try:
                get_location_model().objects.bulk_update(locs_to_update, fields=['p_code', 'is_active', 'admin_level',
                                                                                 'admin_level_name', 'name',
                                                                                 'geom', 'point', 'parent'])
            except IntegrityError as e:
                message = "Duplicates found on update"
                logger.exception(e)
                logger.exception(message)
                raise CartoException(message)

            try:
                get_location_model().objects.bulk_create(locs_to_create)
            except IntegrityError as e:
                message = "Duplicates found on create"
                logger.exception(e)
                logger.exception(message)
                raise CartoException(message)

        logger.info("Rebuilding the tree, have patience")
        get_location_model().objects.rebuild()
        logger.info("Rebuilt")
        return new, updated, skipped, error

    def clean_upper_level(self):
        """
        Check upper level active locations with no reference
        - delete if is leaf
        - deactivate if all children are inactive (doesn't exist an active child)
        """
        logging.info('Clean upper level')
        qs = get_location_model().objects.filter(admin_level=self.carto.admin_level - 1, is_active=False)
        number_of_inactive_parents = qs.count()
        # by default has_related_records excludes self.
        # so we need to make sure that the locations have no children (only leaves)
        qs = qs.filter(children__isnull=True)
        has_related, affected = has_related_records(qs, get_location_model())
        # exclude all locations in use
        qs = qs.exclude(pk__in=affected)
        logging.info(f'deleting {qs.count()} records out of {number_of_inactive_parents} inactive locs')
        qs.delete()
        logging.info('Parents are now gone!')

    def post_sync(self):
        # update sites
        for site in LocationSite.objects.all():
            parent = site.get_parent_location(site.point)
            if site.parent != parent:
                site.parent = parent
                site.save()

        # update monitoring activities
        for activity in MonitoringActivity.objects.filter(location_site__isnull=False):
            if activity.site.parent != activity.location:
                activity.location = activity.site.parent
                activity.save()

    def handle_obsolete_locations(self, to_deactivate):
        """
        Handle obsolete locations:
        - deactivate referenced locations
        - delete non referenced locations
        """
        logging.info('Clean Obsolete Locations')
        first_top_location = get_location_model().objects.filter(admin_level=0, is_active=True).first()
        loc_qs = get_location_model().objects.filter(p_code__in=to_deactivate)
        # first get ridd of all location sites
        # regardless if this location is archived or not, Sites do not need to be associated with it. We'll get the
        # highest level admin and associate it there, re-association is happening anyway.
        LocationSite.objects.filter(parent__in=loc_qs.values_list('pk')).update(parent=first_top_location)
        # then instead of using collector to chase cascading or other relations use helper
        has_related, affected = has_related_records(loc_qs, get_location_model())
        logger.info(f'Deactivating {affected}')
        if has_related:
            loc_qs.filter(pk__in=affected).update(is_active=False,
                                                  name=Concat(F("name"),
                                                              Value(f" [{datetime.today().strftime('%Y-%m-%d')}]")))
            logger.info('Deleting the rest')
        else:
            logger.info('Deleting all')
        # won't be able to delete the ones with children if the children are somehow related. our check does not
        # look for nested relations to self.
        # update all child locations for the "obsolete locations", leave them orphan; - with the understanding that
        # all previous parent relationships are stored in a separate db for reference or remapped adequately
        # on subsequent children updates.
        get_location_model().objects.filter(parent__in=loc_qs).update(parent=None)
        loc_qs.exclude(pk__in=affected).delete()


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

    schema = get_schema_name_from_task(self, dict)
    eToolsLocationSynchronizer(carto_table_pk, schema).sync()


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
