"""
Model factories used for generating models dynamically for tests
"""
__author__ = 'jcranwellward'

from datetime import datetime, timedelta
from django.db.models.signals import post_save

import factory

from users import models as user_models
from trips import models as trip_models
from funds import models as fund_models
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
        model = user_models.Office

    name = 'An Office'


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.Section

    name = factory.Sequence(lambda n: "section_%d" % n)


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.Country
        django_get_or_create = ('schema_name',)

    name = "Test Country"
    schema_name = 'test'
    domain_url = 'tenant.test.com'


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.UserProfile

    country = factory.SubFactory(CountryFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)
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
    password = factory.PostGenerationMethodCall('set_password', 'test')

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
    from_date = datetime.today().date()
    to_date = from_date + timedelta(days=1)


class LinkedLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = location_models.LinkedLocation

    content_object = factory.SubFactory(TripFactory)
    governorate = factory.SubFactory(GovernorateFactory)
    region = factory.SubFactory(RegionFactory)


class PartnerStaffFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PartnerStaffMember

    title = 'Jedi Master'
    first_name = 'Mace'
    last_name = 'Windu'
    email = factory.Sequence(lambda n: "mace{}@theforce.org".format(n))


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PartnerOrganization

    name = factory.Sequence(lambda n: 'Partner {}'.format(n))

    staff = factory.RelatedFactory(PartnerStaffFactory, 'partner')


class AgreementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.Agreement

    partner = factory.SubFactory(PartnerFactory)
    agreement_type = u'PCA'


class PartnershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PCA

    partner = factory.SubFactory(PartnerFactory)
    agreement = factory.SubFactory(AgreementFactory)
    partnership_type = u'PD'
    title = u'To save the galaxy from the Empire'
    initiation_date = datetime.today()


# class FundingCommitmentFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = partner_models.FundingCommitment
#
#     grant = grant,
#     intervention = factory.SubFactory(PartnershipFactory)
#
#
#     fr_number = models.CharField(max_length=50)
#     wbs = models.CharField(max_length=50)
#     fc_type = models.CharField(max_length=50)
