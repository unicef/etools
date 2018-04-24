# -*- coding: utf-8 -*-

import logging
import random

from django.contrib.gis.db import models
from django.core.cache import cache
from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext as _

from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from mptt.models import MPTTModel, TreeForeignKey

logger = logging.getLogger(__name__)


def get_random_color():
    return '#%02X%02X%02X' % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )


@python_2_unicode_compatible
class GatewayType(models.Model):
    """
    Represents an Admin Type in location-related models.
    """

    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    admin_level = models.PositiveSmallIntegerField(null=True, unique=True, verbose_name=_('Admin Level'))

    class Meta:
        ordering = ['name']
        verbose_name = 'Location Type'

    def __str__(self):
        return self.name


class LocationManager(models.Manager):

    def get_queryset(self):
        return super(LocationManager, self).get_queryset().select_related('gateway')


@python_2_unicode_compatible
class Location(MPTTModel):
    """
    Represents Location, either a point or geospatial object,
    pcode should be unique

    Relates to :model:`locations.GatewayType`
    """

    name = models.CharField(verbose_name=_("Name"), max_length=254)
    gateway = models.ForeignKey(
        GatewayType, verbose_name=_('Location Type'),
        on_delete=models.CASCADE,
    )
    latitude = models.FloatField(
        verbose_name=_("Latitude"),
        null=True,
        blank=True,
    )
    longitude = models.FloatField(
        verbose_name=_("Longitude"),
        null=True,
        blank=True,
    )
    p_code = models.CharField(
        verbose_name=_("P Code"),
        max_length=32,
        blank=True,
        default='',
    )

    parent = TreeForeignKey(
        'self',
        verbose_name=_("Parent"),
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        on_delete=models.CASCADE
    )
    geom = models.MultiPolygonField(
        verbose_name=_("Geo Point"),
        null=True,
        blank=True,
    )
    point = models.PointField(verbose_name=_("Point"), null=True, blank=True)
    created = AutoCreatedField(_('created'))
    modified = AutoLastModifiedField(_('modified'))

    objects = LocationManager()

    def __str__(self):
        # TODO: Make generic
        return u'{} ({} {}: {})'.format(
            self.name,
            self.gateway.name,
            'CERD' if self.gateway.name == 'School' else 'PCode',
            self.p_code if self.p_code else ''
        )

    @property
    def geo_point(self):
        return self.point if self.point else self.geom.point_on_surface if self.geom else ""

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


@python_2_unicode_compatible
class CartoDBTable(MPTTModel):
    """
    Represents a table in CartoDB, it is used to import locations

    Relates to :model:`locations.GatewayType`
    """

    domain = models.CharField(max_length=254, verbose_name=_('Domain'))
    api_key = models.CharField(max_length=254, verbose_name=_('API Key'))
    table_name = models.CharField(max_length=254, verbose_name=_('Table Name'))
    display_name = models.CharField(max_length=254, default='', blank=True, verbose_name=_('Display Name'))
    location_type = models.ForeignKey(
        GatewayType, verbose_name=_('Location Type'),
        on_delete=models.CASCADE,
    )
    name_col = models.CharField(max_length=254, default='name', verbose_name=_('Name Column'))
    pcode_col = models.CharField(max_length=254, default='pcode', verbose_name=_('Pcode Column'))
    parent_code_col = models.CharField(max_length=254, default='', blank=True, verbose_name=_('Parent Code Column'))
    parent = TreeForeignKey(
        'self', null=True, blank=True, related_name='children', db_index=True,
        verbose_name=_('Parent'),
        on_delete=models.CASCADE,
    )
    color = models.CharField(blank=True, default=get_random_color, max_length=7, verbose_name=_('Color'))

    def __str__(self):
        return self.table_name
