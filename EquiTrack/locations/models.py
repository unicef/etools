__author__ = 'unicef'

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


class Governorate(models.Model):
    """
    Represents Admin level as a geospatial boundary

    Relates to :model:`locations.GatewayType`
    """

    name = models.CharField(max_length=45L)
    p_code = models.CharField(max_length=32L, blank=True, null=True)
    gateway = models.ForeignKey(
        GatewayType,
        blank=True, null=True,
        verbose_name='Admin type'
    )
    color = ColorPickerField(null=True, blank=True, default=get_random_color)

    geom = models.MultiPolygonField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Region(models.Model):
    """
    Represents a district, a part of Admin area as a geospatial boundary

    Relates to :model:`locations.GatewayType`
    Relates to :model:`locations.Governorate`
    """

    governorate = models.ForeignKey(Governorate)
    name = models.CharField(max_length=45L)
    p_code = models.CharField(max_length=32L, blank=True, null=True)
    gateway = models.ForeignKey(
        GatewayType,
        blank=True, null=True,
        verbose_name='Admin type'
    )
    color = ColorPickerField(null=True, blank=True, default=get_random_color)

    geom = models.MultiPolygonField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'District'
        ordering = ['name']


class Locality(models.Model):
    """
    Represents Locality, a part of District area as a geospatial boundary

    Relates to :model:`locations.GatewayType`
    Relates to :model:`locations.Region`
    """

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
    color = ColorPickerField(null=True, blank=True, default=get_random_color)


    geom = models.MultiPolygonField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Sub-district'
        ordering = ['name']


class LocationManager(models.Manager):

    def get_queryset(self):
        return super(LocationManager, self).get_queryset().select_related('gateway', 'locality')


class Location(MPTTModel):
    """
    Represents Location, either a point or geospatial ojject,
    pcode should be unique

    Relates to :model:`locations.GatewayType`
    Relates to :model:`locations.Locality`
    """

    name = models.CharField(max_length=254L)
    locality = models.ForeignKey(Locality, null=True, blank=True)
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


class LinkedLocation(models.Model):
    """
    Represents Generic model for linking locations to anything

    Relates to :model:`locations.Governorate`
    Relates to :model:`locations.Region`
    Relates to :model:`locations.Locality`
    Relates to :model:`locations.Location`
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
