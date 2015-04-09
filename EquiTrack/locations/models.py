__author__ = 'jcranwellward'

import random

import logging

from django.db import IntegrityError
from django.contrib.gis.db import models
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from cartodb import CartoDBAPIKey, CartoDBException
from smart_selects.db_fields import ChainedForeignKey
from paintstore.fields import ColorPickerField

logger = logging.getLogger('locations.models')


def get_random_color():
    r = lambda: random.randint(0,255)
    return '#%02X%02X%02X' % (r(), r(), r())


class GatewayType(models.Model):
    name = models.CharField(max_length=64L, unique=True)
    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Governorate(models.Model):
    name = models.CharField(max_length=45L)
    p_code = models.CharField(max_length=32L, blank=True, null=True)
    gateway = models.ForeignKey(
        GatewayType,
        blank=True, null=True,
        verbose_name='Admin type'
    )
    color = ColorPickerField(null=True, blank=True, default=lambda: get_random_color())

    geom = models.MultiPolygonField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Region(models.Model):
    governorate = models.ForeignKey(Governorate)
    name = models.CharField(max_length=45L)
    p_code = models.CharField(max_length=32L, blank=True, null=True)
    gateway = models.ForeignKey(
        GatewayType,
        blank=True, null=True,
        verbose_name='Admin type'
    )
    color = ColorPickerField(null=True, blank=True, default=lambda: get_random_color())

    geom = models.MultiPolygonField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'District'
        ordering = ['name']


class Locality(models.Model):
    region = models.ForeignKey(Region)
    cad_code = models.CharField(max_length=11L)
    cas_code = models.CharField(max_length=11L)
    cas_code_un = models.CharField(max_length=11L)
    name = models.CharField(max_length=128L)
    cas_village_name = models.CharField(max_length=128L)
    p_code = models.CharField(max_length=32L, blank=True, null=True)
    gateway = models.ForeignKey(
        GatewayType,
        blank=True, null=True,
        verbose_name='Admin type'
    )
    color = ColorPickerField(null=True, blank=True, default=lambda: get_random_color())


    geom = models.MultiPolygonField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Sub-district'
        ordering = ['name']


class Location(models.Model):

    name = models.CharField(max_length=254L)
    locality = models.ForeignKey(Locality)
    gateway = models.ForeignKey(GatewayType, verbose_name='Gateway type')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    p_code = models.CharField(max_length=32L, blank=True, null=True)

    point = models.PointField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        #TODO: Make generic
        return u'{} ({} {})'.format(
            self.name,
            self.gateway.name,
            "{}: {}".format(
                'CERD' if self.gateway.name == 'School' else 'PCode',
                self.p_code if self.p_code else ''
            )
        )

    @property
    def point_lat_long(self):
        return "Lat: {}, Long: {}".format(
            self.point.y,
            self.point.x
        )

    class Meta:
        unique_together = ('name', 'gateway', 'p_code')
        ordering = ['name']


class LinkedLocation(models.Model):
    """
    Generic model for linking locations to anything
    """
    governorate = models.ForeignKey(Governorate)
    region = ChainedForeignKey(
        Region,
        chained_field="governorate",
        chained_model_field="governorate",
        show_all=False,
        auto_choose=True,
    )
    locality = ChainedForeignKey(
        Locality,
        chained_field="region",
        chained_model_field="region",
        show_all=False,
        auto_choose=True,
        null=True, blank=True
    )
    location = ChainedForeignKey(
        Location,
        chained_field="locality",
        chained_model_field="locality",
        show_all=False,
        auto_choose=False,
        null=True, blank=True
    )

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        desc = u'{} -> {}'.format(
            self.governorate.name,
            self.region.name,
        )
        if self.locality:
            desc = u'{} -> {}'.format(
                desc,
                self.locality.name
            )
        if self.location:
            desc = u'{} -> {} ({})'.format(
                desc,
                self.location.name,
                self.location.gateway.name
            )

        return desc


class CartoDBTable(models.Model):

    domain = models.CharField(max_length=254)
    api_key = models.CharField(max_length=254)
    table_name = models.CharField(max_length=254)
    display_name = models.CharField(max_length=254, null=True, blank=True)
    location_type = models.ForeignKey(GatewayType)
    name_col = models.CharField(max_length=254, default='name')
    pcode_col = models.CharField(max_length=254, default='pcode')
    parent_code_col = models.CharField(max_length=254, null=True, blank=True)
    color = ColorPickerField(null=True, blank=True, default=lambda: get_random_color())

    def __unicode__(self):
        return self.table_name

    def update_sites_from_cartodb(self):

        client = CartoDBAPIKey(self.api_key, self.domain)

        sites_created = sites_updated = sites_not_added = 0
        try:
            sites = client.sql(
                'select * from {}'.format(self.table_name)
            )
        except CartoDBException as e:
            logging.exception("CartoDB exception occured", exc_info=True)
        else:

            if self.location_type.name == 'Governorate':
                parent, level = None, Governorate
            elif self.location_type.name == 'District':
                parent, level = Governorate, Region
            elif self.location_type.name == 'Sub-district':
                parent, level = Region, Locality
            else:
                parent, level = Locality, Location

            for row in sites['rows']:
                pcode = str(row[self.pcode_col]).strip()
                site_name = row[self.name_col].encode('UTF-8')

                if not site_name or site_name.isspace():
                    logger.warning("No name for site with PCode: {}".format(pcode))
                    sites_not_added += 1
                    continue

                parent_code = None
                parent_instance = None
                if self.parent_code_col and parent:
                    try:
                        parent_code = row[self.parent_code_col]
                        parent_instance = parent.objects.get(p_code=parent_code)
                    except (parent.DoesNotExist, parent.MultipleObjectsReturned) as exp:
                        msg = "{} locality found for parent code: {}".format(
                            'Multiple' if exp is parent.MultipleObjectsReturned else 'No',
                            parent_code
                        )
                        logger.warning(msg)
                        sites_not_added += 1
                        continue

                try:
                    create_args = {
                        'p_code': pcode,
                        'gateway': self.location_type
                    }
                    if parent and parent_instance:
                        create_args[parent.__name__.lower()] = parent_instance
                    location, created = level.objects.get_or_create(**create_args)
                except level.MultipleObjectsReturned:
                    logger.warning("Multiple locations found for: {}, {} ({})".format(
                        self.location_type, site_name, pcode
                    ))
                    sites_not_added += 1
                    continue
                else:
                    if created:
                        sites_created += 1
                    else:
                        sites_updated += 1

                location.name = site_name
                if level is Location:
                    location.point = row['the_geom']
                else:
                    location.geom = row['the_geom']

                try:
                    location.save()
                except IntegrityError as e:
                    logger.exception('Error whilst saving location: {}'.format(site_name))
                    sites_not_added += 1
                    continue

                logger.info('{}: {} ({})'.format(
                    'Added' if created else 'Updated',
                    location.name,
                    self.location_type.name
                ))

        return sites_created, sites_updated, sites_not_added
