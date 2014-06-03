__author__ = 'jcranwellward'

from django.core import urlresolvers
from django.contrib.gis.db import models
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from smart_selects.db_fields import ChainedForeignKey


class Governorate(models.Model):
    name = models.CharField(max_length=45L, unique=True)
    area = models.PolygonField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Region(models.Model):
    governorate = models.ForeignKey(Governorate)
    name = models.CharField(max_length=45L, unique=True)
    area = models.PolygonField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Caza'
        ordering = ['name']


class Locality(models.Model):
    region = models.ForeignKey(Region)
    cad_code = models.CharField(max_length=11L)
    cas_code = models.CharField(max_length=11L)
    cas_code_un = models.CharField(max_length=11L)
    name = models.CharField(max_length=128L)
    cas_village_name = models.CharField(max_length=128L)
    area = models.PolygonField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Cadastral/Locality'
        unique_together = ('name', 'cas_code_un')
        ordering = ['name']


class GatewayType(models.Model):
    name = models.CharField(max_length=64L, unique=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Location(models.Model):

    name = models.CharField(max_length=254L)
    locality = models.ForeignKey(Locality)
    gateway = models.ForeignKey(GatewayType, verbose_name='Gateway type')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    p_code = models.CharField(max_length=32L, blank=True, null=True)

    point = models.PointField()
    objects = models.GeoManager()

    def __unicode__(self):
        return u'{} ({} {})'.format(
            self.name,
            self.gateway.name,
            "{}: {}".format(
                'CERD' if self.gateway.name == 'School' else 'P Code',
                self.p_code if self.p_code else ''
            )
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
    )
    location = ChainedForeignKey(
        Location,
        chained_field="locality",
        chained_model_field="locality",
        show_all=False,
        auto_choose=True
    )

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return u'{} -> {} -> {} -> {} ({})'.format(
            self.governorate.name,
            self.region.name,
            self.locality.name,
            self.location.name,
            self.location.gateway.name
        )

    def view_location(self):
        if self.id:
            url_name = 'admin:{app_label}_{model_name}_{action}'.format(
                app_label=self.location._meta.app_label,
                model_name=self.location._meta.model_name,
                action='change'
            )
            location_url = urlresolvers.reverse(url_name, args=(self.location.id,))
            return u'<a class="btn btn-primary default" ' \
                   u'onclick="return showAddAnotherPopup(this);" ' \
                   u'href="{}" target="_blank">View</a>'.format(location_url)
        return u''
    view_location.allow_tags = True
    view_location.short_description = 'View Location'
