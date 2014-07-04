__author__ = 'jcranwellward'

import random

from django.core import urlresolvers
from django.contrib.gis.db import models
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from cartodb import CartoDBAPIKey, CartoDBException
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

    @property
    def point_lat_long(self):
        return "Lat: {}, Long: {}".format(
            self.point.y,
            self.point.x
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
        auto_choose=False,
        null=True, blank=True
    )

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        desc = u'{} -> {} -> {}'.format(
            self.governorate.name,
            self.region.name,
            self.locality.name,
        )
        if self.location:
            desc = u'{} -> {} ({})'.format(
                desc,
                self.location.name,
                self.location.gateway.name
            )

        return desc


class CartoDBTable(models.Model):

    def update_sites_from_cartodb(
            self,
            api_key,
            username,
            table_name,
            name_col,
            pcode_col,
            latitude_col,
            longitude_col,
            prepend_to_name,
            location_type):

        types = {}
        for type in self.get_location_types('LB'):
            types[type['name']] = type
        type_id = types[location_type]['id']

        admin_levels = {}
        for level in self.get_admin_levels('LB'):
            admin_levels[level['name']] = level

        mapped_locations = {}
        for location in self.get_locations(type_id):
            mapped_locations[str(location['name'].encode('UTF-8'))] = location

        govs_id = admin_levels['Governorate']['id']
        cazas_id = admin_levels['Caza']['id']
        cads_id = admin_levels['Cadastral Area']['id']

        govs = {}
        for gov in self.get_entities(govs_id):
            govs[gov['id']] = gov

        cazas = {}
        for caza in self.get_entities(cazas_id):
            cazas[caza['id']] = caza

        cadastas = {}
        for cada in self.get_entities(cads_id):
            cadastas[cada['code']] = cada

        sites_created = sites_not_added = 0

        cl = CartoDBAPIKey(api_key, username)
        try:
            sites = cl.sql('select * from {}'.format(table_name))
        except CartoDBException as e:
            print ("some error ocurred", e)
        else:

            for row in sites['rows']:
                pcode = row[pcode_col]
                cad_code = row['cad_code']
                site_name = row[name_col].encode('UTF-8')

                if not cad_code:
                    print "No cad code for: {}".format(site_name)
                    sites_not_added += 1
                    continue

                if not site_name or site_name.isspace():
                    print "No name for site with PCode: {}".format(pcode)
                    sites_not_added += 1
                    continue

                site_name = '{}: {}'.format(prepend_to_name, site_name)
                ai_id = None
                if site_name in mapped_locations.keys():
                    print "Existing match for {}, updating...".format(site_name)
                    ai_id = mapped_locations[site_name]['id']
                else:
                    print "No existing match for {}, adding...".format(site_name)

                    try:
                        cad = cadastas[cad_code]
                        caza = cazas[cad['parentId']]
                        govn = govs[caza['parentId']]
                    except KeyError as e:
                        raise e

                    print 'Adding site: {} -> {} -> {} -> {}'.format(
                        govn['name'], caza['name'], cad['name'].encode('UTF-8'), site_name
                    )

                    response = self.call_command(
                        'CreateLocation',
                        **{
                            'id': ai_id if ai_id else random.getrandbits(31),
                            'locationTypeId': type_id,
                            'name': site_name,
                            'axe': 'cerd: {}'.format(pcode),
                            'latitude': row[latitude_col],
                            'longitude': row[longitude_col],
                            'E{}'.format(cads_id): cad['id'],
                            'E{}'.format(cazas_id): caza['id'],
                            'E{}'.format(govs_id): govn['id']
                        }
                    )

                    print response.status_code
                    if response.status_code == 200:
                        sites_created += 1

        return sites_created
