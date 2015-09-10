"""
Model factories used for generating models dynamically for tests
"""
__author__ = 'jcranwellward'

from datetime import datetime, timedelta
from django.db.models.signals import post_save

import factory

from users import models as user_models
from trips import models as trip_models
from reports import models as report_models
from locations import models as location_models
from partners import models as partner_models


class GovernorateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = location_models.Governorate

    name = factory.Sequence(lambda n: 'Gov {}'.format(n))


class RegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = location_models.Region

    name = factory.Sequence(lambda n: 'District {}'.format(n))
    governorate = factory.SubFactory(GovernorateFactory)


class OfficeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = trip_models.Office

    name = 'An Office'
    location = factory.SubFactory(GovernorateFactory)


class SectorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Sector

    name = factory.Sequence(lambda n: "section_%d" % n)


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.UserProfile

    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectorFactory)
    job_title = 'Chief Tester'
    phone_number = '0123456789'
    # We pass in profile=None to prevent UserFactory from creating another profile
    # (this disables the RelatedFactory)
    user = factory.SubFactory('EquiTrack.factories.UserFactory', profile=None)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.User

    username = factory.Sequence(lambda n: "user_%d" % n)
    email = factory.Sequence(lambda n: "user{}@notanemail.com".format(n))

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call ProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(ProfileFactory, 'user')

    @classmethod
    def _generate(cls, create, attrs):
        """Override the default _generate() to disable the post-save signal."""

        # Note: If the signal was defined with a dispatch_uid, include that in both calls.
        post_save.disconnect(user_models.UserProfile.create_user_profile, user_models.User)
        user = super(UserFactory, cls)._generate(create, attrs)
        post_save.connect(user_models.UserProfile.create_user_profile, user_models.User)
        return user


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = trip_models.Trip

    owner = factory.SubFactory(UserFactory)
    supervisor = factory.SubFactory(UserFactory)
    from_date = datetime.today()
    to_date = from_date + timedelta(days=1)


class LinkedLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = location_models.LinkedLocation

    content_object = factory.SubFactory(TripFactory)
    governorate = factory.SubFactory(GovernorateFactory)
    region = factory.SubFactory(RegionFactory)


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PartnerOrganization

    name = factory.Sequence(lambda n: 'Partner {}'.format(n))


class PartnershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PCA

    title = factory.Sequence(lambda n: 'PCA {}'.format(n))
    initiation_date = datetime.today()
    partner = factory.SubFactory(PartnerFactory)
