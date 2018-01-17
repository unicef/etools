from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from decimal import Decimal
import random

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import connection, models
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from waffle.models import BaseModel, CACHE_EMPTY, set_flag
from waffle import managers
from waffle.utils import get_setting, keyfmt, get_cache

from users.models import Country

cache = get_cache()


@python_2_unicode_compatible
class IssueCheckConfig(models.Model):
    """
    Used to enable/disable issue checks at runtime.
    """
    check_id = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return '{}: {}'.format(self.check_id, self.is_active)


@python_2_unicode_compatible
class TenantFlag(BaseModel):
    """
    Associate one or more countries with a Flag.

    'countries' is the only field we add. All other fields are copy/pasted from waffle.Flag.
    """
    name = models.CharField(max_length=100, unique=True, help_text=(
        'The human/computer readable name.'))
    countries = models.ManyToManyField(Country, blank=True, help_text=(
        'Activate this flag for these countries.'))
    everyone = models.NullBooleanField(blank=True, help_text=(
        'Flip this flag on (Yes) or off (No) for everyone, overriding all '
        'other settings. Leave as Unknown to use normally.'))
    percent = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, help_text=(
        'A number between 0.0 and 99.9 to indicate a percentage of users for '
        'whom this flag will be active.'))
    testing = models.BooleanField(default=False, help_text=(
        'Allow this flag to be set for a session for user testing.'))
    superusers = models.BooleanField(default=True, help_text=(
        'Flag always active for superusers?'))
    staff = models.BooleanField(default=False, help_text=(
        'Flag always active for staff?'))
    authenticated = models.BooleanField(default=False, help_text=(
        'Flag always active for authenticate users?'))
    languages = models.TextField(blank=True, default='', help_text=(
        'Activate this flag for users with one of these languages (comma '
        'separated list)'))
    groups = models.ManyToManyField(Group, blank=True, help_text=(
        'Activate this flag for these user groups.'))
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, help_text=(
        'Activate this flag for these users.'))
    rollout = models.BooleanField(default=False, help_text=(
        'Activate roll-out mode?'))
    note = models.TextField(blank=True, help_text=(
        'Note where this Flag is used.'))
    created = models.DateTimeField(default=timezone.now, db_index=True, help_text=(
        'Date when this Flag was created.'))
    modified = models.DateTimeField(default=timezone.now, help_text=(
        'Date when this Flag was last modified.'))

    objects = managers.FlagManager()

    SINGLE_CACHE_KEY = 'FLAG_CACHE_KEY'
    ALL_CACHE_KEY = 'ALL_FLAGS_CACHE_KEY'
    FLAG_COUNTRIES_CACHE_KEY = 'flag:%s:countries'

    class Meta:
        verbose_name_plural = 'Flags'

    def __str__(self):
        return self.name

    def flush(self):
        keys = [
            self._cache_key(self.name),
            keyfmt(get_setting('FLAG_USERS_CACHE_KEY'), self.name),
            keyfmt(get_setting('FLAG_GROUPS_CACHE_KEY'), self.name),
            keyfmt(self.FLAG_COUNTRIES_CACHE_KEY, self.name),
            get_setting('ALL_FLAGS_CACHE_KEY'),
        ]
        cache.delete_many(keys)

    def _get_user_ids(self):
        cache_key = keyfmt(get_setting('FLAG_USERS_CACHE_KEY'), self.name)
        cached = cache.get(cache_key)
        if cached == CACHE_EMPTY:
            return set()
        if cached:
            return cached

        user_ids = set(self.users.all().values_list('pk', flat=True))
        if not user_ids:
            cache.add(cache_key, CACHE_EMPTY)
            return set()

        cache.add(cache_key, user_ids)
        return user_ids

    def _get_group_ids(self):
        cache_key = keyfmt(get_setting('FLAG_GROUPS_CACHE_KEY'), self.name)
        cached = cache.get(cache_key)
        if cached == CACHE_EMPTY:
            return set()
        if cached:
            return cached

        group_ids = set(self.groups.all().values_list('pk', flat=True))
        if not group_ids:
            cache.add(cache_key, CACHE_EMPTY)
            return set()

        cache.add(cache_key, group_ids)
        return group_ids

    def _get_country_ids(self):
        cache_key = keyfmt(self.FLAG_COUNTRIES_CACHE_KEY, self.name)
        cached = cache.get(cache_key)
        if cached == CACHE_EMPTY:
            return set()
        if cached:
            return cached

        country_ids = set(self.countries.all().values_list('pk', flat=True))
        if not country_ids:
            cache.add(cache_key, CACHE_EMPTY)
            return set()

        cache.add(cache_key, country_ids)
        return country_ids

    def is_active_for_user(self, user):
        if self.authenticated and user.is_authenticated():
            return True

        if self.staff and user.is_staff:
            return True

        if self.superusers and user.is_superuser:
            return True

        user_ids = self._get_user_ids()
        if user.pk in user_ids:
            return True

        group_ids = self._get_group_ids()
        user_groups = set(user.groups.all().values_list('pk', flat=True))
        if group_ids.intersection(user_groups):
            return True

        return None

    def _is_active_for_request(self, request):
        if hasattr(request, 'tenant'):
            country_ids = self._get_country_ids()
            if request.tenant and request.tenant.id in country_ids:
                return True
        return self.is_active_for_user(request.user)

    def _is_active_for_language(self, request):
        if self.languages:
            languages = [ln.strip() for ln in self.languages.split(',')]
            if request.LANGUAGE_CODE in languages:
                return True
        return None

    def is_active(self, request):
        if not self.pk:
            return get_setting('FLAG_DEFAULT')

        if get_setting('OVERRIDE'):
            if self.name in request.GET:
                return request.GET[self.name] == '1'

        if self.everyone:
            return True
        elif self.everyone is False:
            return False

        if self.testing:  # Testing mode is on.
            tc = get_setting('TEST_COOKIE') % self.name
            if tc in request.GET:
                on = request.GET[tc] == '1'
                request.waffle_tests = getattr(request, 'waffle_tests', {})
                request.waffle_tests[self.name] = on
                return on
            if tc in request.COOKIES:
                return request.COOKIES[tc] == 'True'

        active_for_language = self._is_active_for_language(request)
        if active_for_language is not None:
            return active_for_language

        active_for_request = self._is_active_for_request(request)
        if active_for_request is not None:
            return active_for_request

        if self.percent and self.percent > 0:
            if self.name in getattr(request, 'waffles', {}):
                return request.waffles[self.name][0]

            cookie = get_setting('COOKIE') % self.name
            if cookie in request.COOKIES:
                flag_active = (request.COOKIES[cookie] == 'True')
                set_flag(request, self.name, flag_active, self.rollout)
                return flag_active

            if Decimal(str(random.uniform(0, 100))) <= self.percent:
                set_flag(request, self.name, True, self.rollout)
                return True
            set_flag(request, self.name, False, self.rollout)

        return False


class TenantSwitchManager(managers.BaseManager):
    KEY_SETTING = 'ALL_SWITCHES_CACHE_KEY'

    def get_queryset(self):
        return super(TenantSwitchManager, self).get_queryset().prefetch_related('countries')


@python_2_unicode_compatible
class TenantSwitch(BaseModel):
    """
    Associate one or more countries with a Switch.

    'countries' is the only field we add. All other fields are copy/pasted from waffle.Switch.
    """
    name = models.CharField(max_length=100, unique=True,
                            help_text='The human/computer readable name.')
    active = models.BooleanField(default=False, help_text=(
        'Is this switch active?'))
    countries = models.ManyToManyField(Country, blank=True, help_text=(
        'Activate this switch for these countries.'))
    note = models.TextField(blank=True, help_text=(
        'Note where this Switch is used.'))
    created = models.DateTimeField(default=timezone.now, db_index=True,
                                   help_text=('Date when this Switch was created.'))
    modified = models.DateTimeField(default=timezone.now, help_text=(
        'Date when this Switch was last modified.'))

    objects = TenantSwitchManager()

    SINGLE_CACHE_KEY = 'SWITCH_CACHE_KEY'
    ALL_CACHE_KEY = 'ALL_SWITCHES_CACHE_KEY'

    class Meta:
        verbose_name_plural = 'Switches'

    def __str__(self):
        return self.name

    def is_active(self):
        "Is this switch on for this tenant?"
        if not self.pk:
            # Nonexistent flag, return False
            return False
        if connection.tenant in self.countries.all():
            return self.active
        return False
