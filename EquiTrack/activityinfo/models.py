__author__ = 'jcranwellward'

from datetime import datetime

from django.db import models

from activtyinfo_client import ActivityInfoClient

from partners.models import PCA, IndicatorProgress


class Database(models.Model):

    ai_id = models.PositiveIntegerField(
        unique=True,
        verbose_name='ActivityInfo ID'
    )
    name = models.CharField(max_length=254)
    username = models.CharField(max_length=254)
    password = models.CharField(max_length=254)

    # read only fields
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
            raise Exception(
                'DB with ID {} not found in ActivityInfo'.format(
                    self.ai_id
                ))

        db_info = client.get_database(self.ai_id)
        self.name = db_info['name']
        self.description = db_info['description']
        self.ai_country_id = db_info['country']['id']
        self.country_name = db_info['country']['name']
        self.save()

        objects = 0
        try:
            for partner in db_info['partners']:
                try:
                    ai_partner = Partner.objects.get(ai_id=partner['id'])
                except Partner.DoesNotExist:
                    ai_partner = Partner(ai_id=partner['id'])
                    objects += 1
                ai_partner.name = partner['name']
                ai_partner.full_name = partner['fullName']
                ai_partner.database = self
                ai_partner.save()

            for activity in db_info['activities']:
                try:
                    ai_activity = Activity.objects.get(ai_id=activity['id'])
                except Activity.DoesNotExist:
                    ai_activity = Activity(ai_id=activity['id'])
                    objects += 1
                ai_activity.name = activity['name']
                ai_activity.location_type = activity['locationType']['name']
                ai_activity.database = self
                ai_activity.save()

                for indicator in activity['indicators']:
                    try:
                        ai_indicator = Indicator.objects.get(ai_id=indicator['id'])
                    except Indicator.DoesNotExist:
                        ai_indicator = Indicator(ai_id=indicator['id'])
                        objects += 1
                    ai_indicator.name = indicator['name']
                    ai_indicator.units = indicator['units']
                    ai_indicator.category = indicator['category']
                    ai_indicator.activity = ai_activity
                    ai_indicator.save()

                for attribute_group in activity['attributeGroups']:
                    try:
                        ai_attribute_group = AttributeGroup.objects.get(ai_id=attribute_group['id'])
                    except AttributeGroup.DoesNotExist:
                        ai_attribute_group = AttributeGroup(ai_id=attribute_group['id'])
                        objects += 1
                    ai_attribute_group.name = attribute_group['name']
                    ai_attribute_group.multiple_allowed = attribute_group['multipleAllowed']
                    ai_attribute_group.mandatory = attribute_group['mandatory']
                    ai_attribute_group.activity = ai_activity
                    ai_attribute_group.save()

                    for attribute in attribute_group['attributes']:
                        try:
                            ai_attribute = Attribute.objects.get(ai_id=attribute['id'])
                        except Attribute.DoesNotExist:
                            ai_attribute = Attribute(ai_id=attribute['id'])
                            objects += 1
                        ai_attribute.name = attribute['name']
                        ai_attribute.attribute_group = ai_attribute_group
                        ai_attribute.save()

        except Exception as e:
            raise e

        return objects

    def import_reports(self):

        client = ActivityInfoClient(self.username, self.password)

        reports = 0
        # Select all indicators that are included in Active PCAs,
        # and have linked indicators and a matching partner in AI
        for progress in IndicatorProgress.objects.filter(
                programmed__gt=0,
                pca_sector__pca__status__in=[PCA.ACTIVE, PCA.IMPLEMENTED],
                indicator__activity_info_indicators__isnull=False,
                pca_sector__pca__partner__activity_info_partner__isnull=False):

            # for each selected indicator get the related AI indicators (one-to-many)
            for ai_indicator in progress.indicator.activity_info_indicators.all():
                attributes = ai_indicator.activity.attributegroup_set.all()
                funded_by = attributes.get(name='Funded by')

                # query AI for matching site records for partner, activity, indicator
                sites = client.get_sites(
                    partner=progress.pca.partner.activity_info_partner.ai_id
                    if progress.pca.partner.activity_info_partner else None,
                    activity=ai_indicator.activity.ai_id,
                    indicator=ai_indicator.ai_id,
                    attribute=funded_by.attribute_set.get(name='UNICEF').ai_id,
                )

                # for those marching sites, create partner report instances
                for site in sites:
                    for month, indicators in site['monthlyReports'].items():
                        for indicator in indicators:
                            if indicator['indicatorId'] == ai_indicator.ai_id and indicator['value']:
                                report, created = PartnerReport.objects.get_or_create(
                                    pca=progress.pca,
                                    ai_partner=progress.pca.partner.activity_info_partner,
                                    indicator=progress.indicator,
                                    ai_indicator=ai_indicator,
                                    location=site['location']['name'],
                                    month=datetime.strptime(month+'-15', '%Y-%m-%d'),
                                    indicator_value=indicator['value']
                                )
                                if created:
                                    reports += 1
        return reports


class Partner(models.Model):

    ai_id = models.PositiveIntegerField(unique=True)
    database = models.ForeignKey(Database)
    name = models.CharField(max_length=254)
    full_name = models.CharField(max_length=254, null=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Activity(models.Model):

    ai_id = models.PositiveIntegerField(unique=True)
    database = models.ForeignKey(Database)
    name = models.CharField(max_length=254)
    location_type = models.CharField(max_length=254)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'activities'


class Indicator(models.Model):

    ai_id = models.PositiveIntegerField(unique=True)
    activity = models.ForeignKey(Activity)
    name = models.CharField(max_length=254)
    units = models.CharField(max_length=254)
    category = models.CharField(max_length=254, null=True)

    def __unicode__(self):
        return self.name


class AttributeGroup(models.Model):

    activity = models.ForeignKey(Activity)
    ai_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=254)
    multiple_allowed = models.BooleanField()
    mandatory = models.BooleanField()

    def __unicode__(self):
        return self.name


class Attribute(models.Model):

    attribute_group = models.ForeignKey(AttributeGroup)
    ai_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=254)


# class PartnerReport(models.Model):
#
#     pca = models.ForeignKey(PCA)
#     indicator = models.ForeignKey('reports.Indicator')
#     ai_partner = models.ForeignKey(Partner)
#     ai_indicator = models.ForeignKey(Indicator)
#     location = models.CharField(max_length=254)
#     month = models.DateField()
#     indicator_value = models.IntegerField()
#     created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
#
#     class Meta:
#         ordering = ['-month']

