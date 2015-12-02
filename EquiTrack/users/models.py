from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from djangosaml2.signals import pre_user_save

from django.db import transaction

from tenant_schemas.models import TenantMixin
from partners.models import PartnerStaffMember

User.__unicode__ = lambda user: user.get_full_name()
User._meta.ordering = ['first_name']


class Country(TenantMixin):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __unicode__(self):
        return self.name


class Office(models.Model):
    name = models.CharField(max_length=254)
    zonal_chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        related_name='offices',
        verbose_name='Chief'
    )

    def __unicode__(self):
        return self.name


class UserProfile(models.Model):

    user = models.OneToOneField(User, related_name='profile')
    partner_staff_member = models.IntegerField(
        null=True,
        blank=True
    )
    country = models.ForeignKey(Country, null=True, blank=True)
    country_override = models.ForeignKey(Country, null=True, blank=True, related_name="country_override")
    section = models.ForeignKey(Section, null=True, blank=True)
    office = models.ForeignKey(Office, null=True, blank=True)
    job_title = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    installation_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='Device ID')

    def username(self):
        return self.user.username

    def __unicode__(self):
        return u'User profile for {}'.format(
            self.user.get_full_name()
        )

    @classmethod
    def create_user_profile(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create user profiles automatically
        """
        if created:
            cls.objects.create(user=instance)

    @classmethod
    def custom_update_user(cls, sender, attributes, user_modified, **kwargs):
        adfs_country = attributes.get("countryName")
        new_country = None
        if sender.profile.country_override:
            new_country = sender.profile.country_override
        elif adfs_country:
            try:
                new_country = Country.objects.get(name=adfs_country[0])
            except Country.DoesNotExist:
                return False
        if new_country and new_country != sender.profile.country:
            sender.profile.country = new_country
            sender.profile.save()
            return True
        return False


post_save.connect(UserProfile.create_user_profile, sender=User)


def create_user(sender, instance, created, **kwargs):
    if created:
        user, ucreated = User.objects.get_or_create(username=instance.email)

        # there should be a check before PartnerStaffMember is saved to insure that no users
        # with that email address are present in the user model
        if not ucreated and user.profile.partner_staff_member:
            instance.delete()
            raise Exception("Something unexpected happened.")

        # TODO: here we have a decision.. either we update the user with the info just received from
        # TODO: or we update the instance with the user we already have. this might have implications on login.
        with transaction.atomic():
            user.email = instance.email
            user.first_name = instance.first_name
            user.last_name = instance.last_name
            user.save()
            user.profile.partner_staff_member = instance.id
            user.profile.save()



def delete_partner_relationship(sender, instance, **kwargs):
    try:
        profile = UserProfile.objects.filter(partner_staff_member=instance.id).get()
        with transaction.atomic():
            profile.partner_staff_member = None
            profile.save()
            profile.user.is_active = False
            profile.user.save()
    except:
        pass

pre_delete.connect(delete_partner_relationship, sender=PartnerStaffMember)
post_save.connect(create_user, sender=PartnerStaffMember)

pre_user_save.connect(UserProfile.custom_update_user)
