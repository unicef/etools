__author__ = 'jcranwellward'

import random

import logging

from django.db import IntegrityError, connection
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.core.cache import cache
from django.contrib.gis.db import models
from django.contrib.contenttypes.models import ContentType

from mptt.models import MPTTModel, TreeForeignKey
from cartodb import CartoDBAPIKey, CartoDBException
from smart_selects.db_fields import ChainedForeignKey
from paintstore.fields import ColorPickerField

logger = logging.getLogger('locations.models')


def get_random_color():
    r = lambda: random.randint(0,255)
    return '#%02X%02X%02X' % (r(), r(), r())


class GatewayType(models.Model):
    """
    Represents an Admin Type in location-related models.
    """

    name = models.CharField(max_length=64L, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Location Type'

    def __unicode__(self):
        return self.name


class LocationManager(models.Manager):

    def get_queryset(self):
        return super(LocationManager, self).get_queryset().select_related('gateway')


class Location(MPTTModel):
    """
    Represents Location, either a point or geospatial ojject,
    pcode should be unique

    Relates to :model:`locations.GatewayType`
    """

    name = models.CharField(max_length=254L)
    gateway = models.ForeignKey(GatewayType, verbose_name='Location Type')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    p_code = models.CharField(max_length=32L, blank=True, null=True)

    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
    geom = models.MultiPolygonField(null=True, blank=True)
    point = models.PointField(null=True, blank=True)
    objects = models.GeoManager()

    objects = LocationManager()

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
    def geo_point(self):
        return self.point if self.point else self.geom.point_on_surface


    @property
    def point_lat_long(self):
        return "Lat: {}, Long: {}".format(
            self.point.y,
            self.point.x
        )

    class Meta:
        unique_together = ('name', 'gateway', 'p_code')
        ordering = ['name']


@receiver(post_delete, sender=Location)
@receiver(post_save, sender=Location)
def invalidate_locations_etag(sender, instance, **kwargs):
    """
    Invalidate the locations etag in the cache on every change.
    """
    schema_name = connection.schema_name
    cache.delete("{}-locations-etag".format(schema_name))


class CartoDBTable(MPTTModel):
    """
    Represents a table in CartoDB, it is used to import lacations

    Relates to :model:`locations.GatewayType`
    """

    domain = models.CharField(max_length=254)
    api_key = models.CharField(max_length=254)
    table_name = models.CharField(max_length=254)
    display_name = models.CharField(max_length=254, null=True, blank=True)
    location_type = models.ForeignKey(GatewayType)
    name_col = models.CharField(max_length=254, default='name')
    pcode_col = models.CharField(max_length=254, default='pcode')
    parent_code_col = models.CharField(max_length=254, null=True, blank=True)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
    color = ColorPickerField(null=True, blank=True, default=get_random_color)

    def __unicode__(self):
        return self.table_name
