import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import (
    _user_get_permissions,
    _user_has_module_perms,
    _user_has_perm,
    AbstractBaseUser,
    Group,
    Permission,
    UserManager,
)
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import connection, models, transaction
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from django_tenants.models import TenantMixin
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel

from etools.applications.organizations.models import Organization
from etools.applications.users.mixins import PARTNER_ACTIVE_GROUPS
from etools.libraries.djangolib.models import GroupWrapper

logger = logging.getLogger(__name__)


def preferences_default_dict():
    return {'language': settings.LANGUAGE_CODE}


class PermissionsMixin(models.Model):
    """
    Add the fields and methods necessary to support the Group and Permission
    models using the ModelBackend.
    """
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="user_set",
        related_query_name="user",
    )

    class Meta:
        abstract = True

    def get_user_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has directly.
        Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, 'user')

    def get_group_permissions(self, obj=None):
        """
        Return a list of permission strings that this user has through their
        groups. Query all available auth backends. If an object is passed in,
        return only permissions matching this object.
        """
        return _user_get_permissions(self, obj, 'group')

    def get_all_permissions(self, obj=None):
        return _user_get_permissions(self, obj, 'all')

    def has_perm(self, perm, obj=None):
        """
        Return True if the user has the specified permission. Query all
        available auth backends, but return immediately if any backend returns
        True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        """
        Return True if the user has each of the specified permissions. If
        object is passed, check if the user has all required perms for it.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        """
        Return True if the user has any permissions in the given app label.
        Use similar logic as has_perm(), above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)


class UsersManager(UserManager):

    def get_queryset(self):
        return super().get_queryset() \
            .select_related('profile', 'profile__country', 'profile__country_override',
                            'profile__organization', 'profile__office')

    def base_qs(self):
        return super().get_queryset().prefetch_related(None).only(
            'id',
            'first_name',
            'last_name',
            'middle_name',
            'is_active',
            'email'
        )


class User(TimeStampedModel, AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ['email']

    username = models.CharField(_("username"), max_length=256, unique=True)
    email = models.EmailField(_('email address'), unique=True)
    password = models.CharField(_("password"), max_length=128)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    middle_name = models.CharField(_('middle_name'), max_length=50, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    last_login = models.DateTimeField(_('last login'), blank=True, null=True)
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff'), default=False)
    is_superuser = models.BooleanField(_('superuser'), default=False)

    preferences = models.JSONField(default=preferences_default_dict)

    objects = UsersManager()

    class Meta:
        db_table = "auth_user"
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["first_name"]

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def __str__(self):
        return '{} {} ({})'.format(
            self.first_name,
            self.last_name,
            self.profile.organization.name if self.profile.organization else '-'
        )

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = ' '.join([
            self.first_name,
            self.middle_name,
            self.last_name,
        ])
        return full_name.strip().replace("  ", " ")

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def is_unicef_user(self):
        return self.email.endswith(settings.UNICEF_USER_EMAIL)

    @cached_property
    def is_partnership_manager(self):
        return self.realms.filter(
            country=connection.tenant,
            organization=self.profile.organization,
            group=PartnershipManager.as_group(),
            is_active=True).exists()

    @cached_property
    def full_name(self):
        return self.get_full_name()

    @cached_property
    def partner(self):
        """
        To be used only when fetching the current partner for the authenticated user,
        don't use this in validations
        :return: Only the partner in the current organization selected by the user
        """
        return self.get_partner()

    @cached_property
    def groups(self):
        current_country_realms = self.realms.filter(
            country_id=getattr(connection.tenant, "id", None),
            organization=self.profile.organization,
            is_active=True
        )
        return Group.objects.filter(realms__in=current_country_realms).distinct()

    def get_groups_for_organization_id(self, organization_id, **extra_filters):
        current_country_realms = self.realms.filter(
            country=connection.tenant, organization_id=organization_id, **extra_filters)
        return Group.objects.filter(realms__in=current_country_realms).distinct()

    def get_partner(self):
        """
        To be used only when fetching the current partner for the authenticated user,
        don't use this in validations
        :return: Only the partner in the current organization selected by the user
        """
        realm = self.realms.filter(
            country=connection.tenant,
            organization=self.profile.organization,
            group__name__in=PARTNER_ACTIVE_GROUPS,
            is_active=True,
        ).last()
        if realm:
            try:
                return realm.organization.partner
            except realm.organization._meta.get_field('partner').related_model.DoesNotExist:
                return None
        return None

    def get_admin_url(self):
        info = (self._meta.app_label, self._meta.model_name)
        return reverse('admin:%s_%s_change' % info, args=(self.pk,))

    def update_active_state(self):
        # inactivate an active user if no active realms available:
        if self.is_active and not self.realms.filter(is_active=True).exists():
            self.is_active = False
        # activate an inactive user if it has active realms
        elif not self.is_active and self.realms.filter(is_active=True).exists():
            self.is_active = True
        self.save(update_fields=['is_active'])

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.email != self.email.lower():
            raise ValidationError("Email must be lowercase.")

        if self.pk and not self.is_active:
            self.realms.update(is_active=False)
        super().save(*args, **kwargs)


def custom_dashboards_default():
    return dict(bi_url='')


class Country(TenantMixin):
    """
    Tenant Schema
    Represents a country which has many offices

    Relates to :model:`users.Office`
    """

    name = models.CharField(max_length=100, verbose_name=_('Name'))
    country_short_code = models.CharField(
        max_length=10,
        default='',
        blank=True,
        verbose_name=_('UNICEF Country Reference Code')
    )
    iso3_code = models.CharField(
        max_length=10,
        blank=True,
        default='',
        verbose_name=_("ISO3 Code"),
    )
    long_name = models.CharField(max_length=255, default='', blank=True, verbose_name=_('Long Name'))
    business_area_code = models.CharField(max_length=10, default='', blank=True, verbose_name=_('Business Area Code'))
    latitude = models.DecimalField(
        null=True, blank=True, verbose_name=_('Latitude'), max_digits=8, decimal_places=5,
        validators=[MinValueValidator(Decimal(-90)), MaxValueValidator(Decimal(90))]
    )
    longitude = models.DecimalField(
        null=True, blank=True, max_digits=8, decimal_places=5, verbose_name=_('Longitude'),
        validators=[MinValueValidator(Decimal(-180)), MaxValueValidator(Decimal(180))]
    )
    initial_zoom = models.IntegerField(default=8, verbose_name=_('Initial Zoom'))
    vision_sync_enabled = models.BooleanField(default=True, verbose_name=_('Vision Sync Enabled'))
    vision_last_synced = models.DateTimeField(null=True, blank=True, verbose_name=_('Vision Last Sync'))

    local_currency = models.ForeignKey('publics.Currency',
                                       verbose_name=_('Local Currency'),
                                       related_name='workspaces',
                                       null=True,
                                       on_delete=models.SET_NULL,
                                       blank=True)

    # TODO: rename the related name as it's inappropriate for relating offices to countries.. should be office_countries
    offices = models.ManyToManyField('Office', related_name='offices', verbose_name=_('Offices'), blank=True)
    custom_dashboards = models.JSONField(verbose_name=_('Custom Dashboards'), default=custom_dashboards_default)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('Countries')


class WorkspaceCounter(models.Model):
    TRAVEL_REFERENCE = 'travel_reference_number_counter'
    TRAVEL_INVOICE_REFERENCE = 'travel_invoice_reference_number_counter'

    workspace = models.OneToOneField('users.Country', related_name='counters', verbose_name=_('Workspace'),
                                     on_delete=models.CASCADE)

    # T2F travel reference number counter
    travel_reference_number_counter = models.PositiveIntegerField(
        default=1, verbose_name=_('Travel Reference Number Counter'))
    travel_invoice_reference_number_counter = models.PositiveIntegerField(
        default=1, verbose_name=_('Travel Invoice Reference Number Counter'))

    def get_next_value(self, counter_type):
        assert connection.in_atomic_block, 'Counters should be used only within an atomic block'

        # Locking the row
        counter_model = WorkspaceCounter.objects.select_for_update().get(id=self.id)

        counter_value = getattr(counter_model, counter_type, None)
        if counter_value is None:
            raise AttributeError('Invalid counter type')

        setattr(counter_model, counter_type, counter_value + 1)
        counter_model.save()

        return counter_value

    @classmethod
    def create_counter_model(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create user profiles automatically
        """
        if created:
            cls.objects.create(workspace=instance)

    def __str__(self):
        return self.workspace.name


post_save.connect(WorkspaceCounter.create_counter_model, sender=Country)


class CountryOfficeManager(models.Manager):
    def get_queryset(self):
        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            return super().get_queryset().filter(offices=connection.tenant)
        else:
            # this only gets called on initialization because FakeTenant does not have the model attrs
            return super().get_queryset()


class Office(models.Model):
    """
    Represents an office for the country

    Relates to :model:`AUTH_USER_MODEL`
    """

    name = models.CharField(max_length=254, verbose_name=_('Name'))
    zonal_chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        related_name='offices_old',
        verbose_name='Chief',
        on_delete=models.CASCADE,
    )

    objects = CountryOfficeManager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class UserProfileManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()\
            .select_related('user', 'country', 'country_override', 'organization')


class UserProfile(models.Model):
    """
    Represents a user profile that can have access to many Countries but to one active Country at a time

    Relates to :model:`AUTH_USER_MODEL`
    Relates to :model:`users.Country`
    Relates to :model:`users.Office`
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile', verbose_name=_('User'),
                                on_delete=models.CASCADE)
    # TODO: after migration remove the ability to add blank=True
    guid = models.CharField(max_length=40, unique=True, null=True, verbose_name=_('GUID'))

    # legacy field; to be removed
    _partner_staff_member = models.IntegerField(null=True, blank=True, verbose_name=_('Partner Staff Member'))

    country = models.ForeignKey(
        Country, null=True, blank=True, verbose_name=_('Country'),
        on_delete=models.CASCADE,
    )
    country_override = models.ForeignKey(
        Country, null=True, blank=True, related_name="country_override",
        verbose_name=_('Country Override'),
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        Organization, null=True, blank=True, verbose_name=_('Current Organization'),
        on_delete=models.CASCADE
    )
    office = models.ForeignKey(
        Office, null=True, blank=True, verbose_name=_('Office'),
        on_delete=models.CASCADE,
    )
    job_title = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Job Title'))
    phone_number = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Phone Number'))

    # staff_id needs to be NULLable so we can make it unique while still making it optional
    staff_id = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Staff ID'))
    org_unit_code = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Org Unit Code'))
    org_unit_name = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Org Unit Name'))
    post_number = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Post Number'))
    post_title = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Post Title'))
    # vendor_number needs to be NULLable so we can make it unique while still making it optional
    vendor_number = models.CharField(max_length=32, null=True, blank=True,
                                     unique=True, verbose_name=_('Vendor Number'))
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='supervisee', on_delete=models.SET_NULL,
                                   blank=True, null=True, verbose_name=_('Supervisor'))
    oic = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, verbose_name=_('OIC'),
                            null=True, blank=True)  # related oic_set

    receive_tpm_notifications = models.BooleanField(verbose_name=_('Receive Notifications on TPM Tasks'), default=False)

    # TODO: figure this out when we need to automatically map to groups
    # vision_roles = ArrayField(models.CharField(max_length=20, blank=True, choices=VISION_ROLES),
    #                           blank=True, null=True)

    @property
    def countries_available(self):
        return Country.objects.filter(realms__in=self.user.realms.filter(is_active=True)).distinct()

    @property
    def organizations_available(self):
        current_country_realms = self.user.realms.filter(country=connection.tenant, is_active=True)
        qs = Organization.objects.filter(realms__in=current_country_realms).distinct()

        return qs

    def username(self):
        return self.user.username

    def email(self):
        return self.user.email

    def first_name(self):
        return self.user.first_name

    def middle_name(self):
        return self.user.middle_name

    def last_name(self):
        return self.user.last_name

    def __str__(self):
        return 'User profile for {}'.format(
            self.user.get_full_name()
        )

    class Meta:
        verbose_name_plural = _('User Profile')

    objects = UserProfileManager()

    @classmethod
    def create_user_profile(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create user profiles automatically
        """
        if not cls.objects.filter(user=instance).exists():
            cls.objects.create(user=instance)

    def save(self, **kwargs):

        if self.country_override and self.country != self.country_override:
            self.country = self.country_override

        if self.staff_id == '':
            self.staff_id = None
        if self.vendor_number == '':
            self.vendor_number = None

        super().save(**kwargs)


post_save.connect(UserProfile.create_user_profile, sender=settings.AUTH_USER_MODEL)


class RealmManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('user', 'country', 'organization', 'group')


class Realm(TimeStampedModel):
    user = models.ForeignKey(
        User, verbose_name=_('User'), on_delete=models.CASCADE, related_name='realms'
    )
    country = models.ForeignKey(
        Country, verbose_name=_('Country'), on_delete=models.CASCADE, related_name='realms'
    )
    organization = models.ForeignKey(
        Organization, verbose_name=_('Organization'), on_delete=models.CASCADE, related_name='realms'
    )
    group = models.ForeignKey(
        Group, verbose_name=_('Group'), on_delete=models.CASCADE, related_name='realms'
    )
    is_active = models.BooleanField(_('Active'), default=True)

    history = GenericRelation(
        'unicef_snapshot.Activity', object_id_field='target_object_id',
        content_type_field='target_content_type'
    )
    tracker = FieldTracker(
        fields=['user', 'country', 'organization', 'group', 'is_active']
    )

    objects = RealmManager()

    class Meta:
        verbose_name = _("Realm")
        verbose_name_plural = _("Realms")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'country', 'organization', 'group'], name='unique_realm')
        ]
        indexes = [
            models.Index(fields=['user', 'country', 'organization'])
        ]

    def __str__(self):
        data = f"{self.user.email} - {self.country.name} - {self.organization}: " \
               f"{self.group.name if self.group else ''}"
        if not self.is_active:
            data = "[Inactive] " + data
        return data

    @transaction.atomic()
    def save(self, **kwargs):
        super().save(**kwargs)

        self.user.update_active_state()


class StagedUser(models.Model):
    """
    Represents the users awaiting review in AMP.
    When a user is accepted by a User Reviewer, a new user will be created along with its realms.
    """

    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'

    REQUEST_STATE = (
        (PENDING, _("Pending")),
        (ACCEPTED, _('Accepted')),
        (DECLINED, _('Declined')),
    )

    user_json = models.JSONField()

    requester = models.ForeignKey(User, related_name="requested_users", on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, related_name="reviewed_users", null=True, blank=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    request_state = models.CharField(max_length=10, choices=REQUEST_STATE, default=PENDING)
    state_timestamp = models.DateTimeField(_('state timestamp'), auto_now=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.requester == self.reviewer:
            raise ValidationError(_("The requester cannot review its own requests."))

        super().save(*args, **kwargs)


IPViewer = GroupWrapper(code='ip_viewer', name='IP Viewer')
IPEditor = GroupWrapper(code='ip_editor', name='IP Editor')
IPAdmin = GroupWrapper(code='ip_admin', name='IP Admin')
IPAuthorizedOfficer = GroupWrapper(code='ip_authorized_officer', name='IP Authorized Officer')
PartnershipManager = GroupWrapper(code='partnership_manager', name='Partnership Manager')
UserReviewer = GroupWrapper(code='partnership_manager', name='User Reviewer')
