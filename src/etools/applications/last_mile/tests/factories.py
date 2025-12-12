from django.contrib.gis.geos import GEOSGeometry

import factory
from unicef_locations.tests.factories import LocationFactory

from etools.applications.last_mile import models
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class PointOfInterestTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PointOfInterestType


class PointOfInterestTypeMappingFactory(factory.django.DjangoModelFactory):
    primary_type = factory.SubFactory(PointOfInterestTypeFactory)
    secondary_type = factory.SubFactory(PointOfInterestTypeFactory)

    class Meta:
        model = models.PointOfInterestTypeMapping


class PointOfInterestFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    poi_type = factory.SubFactory(PointOfInterestTypeFactory)
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))
    parent = factory.LazyFunction(lambda: LocationFactory(admin_level=0))

    class Meta:
        model = models.PointOfInterest

    @factory.post_generation
    def partner_organizations(self, create, extracted, data=None, **kwargs):
        if not create:
            return
        extracted = (extracted or []) + (data or [])

        if extracted:
            for partner in extracted:
                self.partner_organizations.add(partner)
        else:
            self.partner_organizations.add(PartnerFactory())


class UserPointOfInterestFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    point_of_interest = factory.SubFactory(PointOfInterestFactory)

    class Meta:
        model = models.UserPointsOfInterest


class MaterialFactory(factory.django.DjangoModelFactory):
    number = factory.Sequence(lambda n: n + 1)
    short_description = factory.Sequence(lambda n: 'Material short description {}'.format(n))

    class Meta:
        model = models.Material


class TransferFactory(factory.django.DjangoModelFactory):
    unicef_release_order = factory.Sequence(lambda n: n + 1)
    destination_point = factory.SubFactory(PointOfInterestFactory)
    origin_point = factory.SubFactory(PointOfInterestFactory)
    partner_organization = factory.SubFactory(PartnerFactory)

    class Meta:
        model = models.Transfer


class ItemFactory(factory.django.DjangoModelFactory):
    quantity = factory.Sequence(lambda n: n + 1)
    material = factory.SubFactory(MaterialFactory)
    transfer = factory.SubFactory(TransferFactory)

    class Meta:
        model = models.Item


class LastMileProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    status = models.Profile.ApprovalStatus.APPROVED
    review_notes = factory.Sequence(lambda n: 'Review notes {}'.format(n))

    class Meta:
        model = models.Profile


class TransferHistoryFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.TransferHistory


class ItemTransferHistoryFactory(factory.django.DjangoModelFactory):
    item = factory.SubFactory(ItemFactory)
    transfer = factory.SubFactory(TransferFactory)

    class Meta:
        model = models.ItemTransferHistory


class PartnerMaterialFactory(factory.django.DjangoModelFactory):
    material = factory.SubFactory(MaterialFactory)
    partner_organization = factory.SubFactory(PartnerFactory)

    class Meta:
        model = models.PartnerMaterial


class ItemAuditConfigurationFactory(factory.django.DjangoModelFactory):

    name = factory.Sequence(lambda n: 'Item Audit Configuration {}'.format(n))
    is_enabled = True
    track_system_users = True
    tracked_fields = models.default_tracked_fields()
    excluded_user_ids = []
    max_entries_per_item = models.AuditConfiguration.DEFAULT_MAX_ENTRIES_PER_ITEM
    fk_field_mappings = models.default_fk_field_mappings()
    is_active = True

    class Meta:
        model = models.AuditConfiguration
