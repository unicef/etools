__author__ = 'jcranwellward'

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from activtyinfo_client import ActivityInfoClient

from partners.models import PCA, IndicatorProgress


class Database(models.Model):

    ai_id = models.PositiveIntegerField()
    username = models.CharField(max_length=254)
    password = models.CharField(max_length=254)

    # read only fields
    name = models.CharField(max_length=254, null=True)
    description = models.CharField(max_length=254, null=True)
    country_name = models.CharField(max_length=254, null=True)
    ai_country_id = models.PositiveIntegerField(null=True)

    def __unicode__(self):
        return self.name

    def import_data(self):
        """
        Import all activities, indicators and partners from
        a ActivityInfo database specified by the AI ID
        """
        client = ActivityInfoClient(self.username, self.password)

        dbs = client.get_databases()
        db_ids = [db['id'] for db in dbs]
        if self.ai_id not in db_ids:
            raise Exception('self not found in ActivityInfo')

        db_info = client.get_database(self.ai_id)
        self.name = db_info['name']
        self.description = db_info['description']
        self.ai_country_id = db_info['country']['id']
        self.country_name = db_info['country']['name']

        objects = 0
        for partner in db_info['partners']:
            ai_partner, created = Partner.objects.get_or_create(
                ai_id=partner['id'],
                name=partner['name'],
                full_name=partner['fullName'],
                database=self
            )
            if created:
                objects += 1

        for activity in db_info['activities']:
            ai_activity, created = Activity.objects.get_or_create(
                ai_id=activity['id'],
                name=activity['name'],
                location_type=activity['locationType']['name'],
                database=self
            )
            if created:
                objects += 1

            for indicator in activity['indicators']:
                ai_indicator, created = Indicator.objects.get_or_create(
                    ai_id=indicator['id'],
                    name=indicator['name'],
                    units=indicator['units'],
                    category=indicator['category'],
                    activity=ai_activity
                )
                if created:
                    objects += 1
        self.save()
        return objects

    def import_reports(self):

        client = ActivityInfoClient(self.username, self.password)

        reports = 0
        for progress in IndicatorProgress.objects.filter(
                activity_info_indicator__isnull=False):

            ai_indicator = progress.indicator.activity_info_indicator
            sites = client.get_sites(
                activity=ai_indicator.activity.ai_id,
                indicator=ai_indicator.ai_id
            )

            for site in sites:
                ai_partner = Partner.objects.get(ai_id=site['partner']['id'])
                if progress.pca.partner.activity_info_partner == ai_partner:
                    report, created = PartnerReport.objects.get_or_create(
                        pca=progress.pca,
                        indicator=progress.indicator,
                        indicator_value=site['indicatorValues'][ai_indicator.ai_id]
                    )
                    if created:
                        reports += 1
        return reports


class Partner(models.Model):

    ai_id = models.PositiveIntegerField()
    database = models.ForeignKey(Database)
    name = models.CharField(max_length=254)
    full_name = models.CharField(max_length=254, null=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Activity(models.Model):

    ai_id = models.PositiveIntegerField()
    database = models.ForeignKey(Database)
    name = models.CharField(max_length=254)
    location_type = models.CharField(max_length=254)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'activities'


class Indicator(models.Model):

    ai_id = models.PositiveIntegerField()
    activity = models.ForeignKey(Activity)
    name = models.CharField(max_length=254)
    units = models.CharField(max_length=254)
    category = models.CharField(max_length=254, null=True)

    def __unicode__(self):
        return self.name


class PartnerReport(models.Model):

    pca = models.ForeignKey(PCA)
    indicator = models.ForeignKey(Indicator)
    indicator_value = models.IntegerField()

    # content_type = models.ForeignKey(ContentType)
    # object_id = models.PositiveIntegerField()
    # content_object = generic.GenericForeignKey('content_type', 'object_id')
