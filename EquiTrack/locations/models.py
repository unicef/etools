__author__ = 'jcranwellward'

from django.contrib.gis.db import models


class Governorate(models.Model):
    name = models.CharField(max_length=45L)
    area = models.MultiPointField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name


class Region(models.Model):
    governorate = models.ForeignKey(Governorate)
    name = models.CharField(max_length=45L)
    area = models.MultiPointField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name


class Locality(models.Model):
    region = models.ForeignKey(Region)
    cad_code = models.CharField(max_length=11L)
    cas_code = models.CharField(max_length=11L)
    cas_code_un = models.CharField(max_length=11L)
    name = models.CharField(max_length=128L)
    cas_village_name = models.CharField(max_length=128L)
    area = models.MultiPointField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name


class GatewayType(models.Model):
    name = models.CharField(max_length=64L)

    def __unicode__(self):
        return self.name


class Location(models.Model):

    name = models.CharField(max_length=45L, blank=True)
    locality = models.ForeignKey(Locality, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    p_code = models.CharField(max_length=32L, blank=True)

    point = models.PointField(null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name
