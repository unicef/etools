__author__ = 'jcranwellward'

from django.db import models


class Governorate(models.Model):
    name = models.CharField(max_length=45L)


class Region(models.Model):
    governorate = models.ForeignKey(Governorate)
    name = models.CharField(max_length=45L)


class Locality(models.Model):
    region = models.ForeignKey(Region)
    cad_code = models.CharField(max_length=11L)
    cas_code = models.CharField(max_length=11L)
    cas_code_un = models.CharField(max_length=11L)
    name = models.CharField(max_length=128L)
    cas_village_name = models.CharField(max_length=128L)


class GatewayType(models.Model):
    name = models.CharField(max_length=64L)


class Location(models.Model):
    locality = models.ForeignKey(Locality)
    name = models.CharField(max_length=45L, blank=True)
    latitude = models.DecimalField(null=True, max_digits=12, decimal_places=5, blank=True)
    longitude = models.DecimalField(null=True, max_digits=12, decimal_places=5, blank=True)
    p_code = models.CharField(max_length=32L, blank=True)
