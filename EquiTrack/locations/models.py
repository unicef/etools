__author__ = 'jcranwellward'

from django.contrib.gis.db import models


class Governorate(models.Model):
    name = models.CharField(max_length=45L, unique=True)
    area = models.PolygonField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name


class Region(models.Model):
    governorate = models.ForeignKey(Governorate)
    name = models.CharField(max_length=45L, unique=True)
    area = models.PolygonField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Caza'


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


class GatewayType(models.Model):
    name = models.CharField(max_length=64L, unique=True)

    def __unicode__(self):
        return self.name


class Location(models.Model):

    name = models.CharField(max_length=45L)
    locality = models.ForeignKey(Locality)
    gateway = models.ForeignKey(GatewayType, verbose_name='Gateway type')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    p_code = models.CharField(max_length=32L, blank=True)

    point = models.PointField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return u'{} ({})'.format(self.name, self.gateway.name)

    class Meta:
        unique_together = ('name', 'p_code')
