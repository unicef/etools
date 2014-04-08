__author__ = 'jcranwellward'

from django.db import models


class Database(models.Model):

    ai_id = models.PositiveIntegerField(unique=True)
    username = models.CharField(max_length=254)
    passowrd = models.CharField(max_length=254)

    # read only fields
    name = models.CharField(max_length=254, null=True)
    description = models.CharField(max_length=254, null=True)
    country_name = models.CharField(max_length=254, null=True)
    ai_country_id = models.PositiveIntegerField(null=True)


class Partner(models.Model):

    ai_id = models.PositiveIntegerField()
    database = models.ForeignKey(Database)
    name = models.CharField(max_length=254)
    full_name = models.CharField(max_length=254)


class Activity(models.Model):

    ai_id = models.PositiveIntegerField()
    database = models.ForeignKey(Database)
    name = models.CharField(max_length=254)
    location_type = models.CharField(max_length=254)


class Indicator(models.Model):

    ai_id = models.PositiveIntegerField()
    activity = models.ForeignKey(Activity)
    name = models.CharField(max_length=254)
    description = models.CharField(max_length=254)
    units = models.CharField(max_length=254)
    category = models.CharField(max_length=254)
