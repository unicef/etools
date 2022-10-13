from django.conf.global_settings import LANGUAGES
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from etools.applications.audit.models import Auditor
from etools.applications.organizations.models import Organization
from etools.applications.users.mixins import DynamicFieldsSerializerMixin, GroupEditPermissionMixin
from etools.applications.users.models import Country, Realm, UserProfile
from etools.applications.users.serializers import GroupSerializer, SimpleCountrySerializer, SimpleOrganizationSerializer
from etools.applications.users.validators import EmailValidator, ExternalUserValidator

# temporary list of Countries that will use the Auditor Portal Module.
# Logic be removed once feature gating is in place
AP_ALLOWED_COUNTRIES = [
    'UAT',
    'Lebanon',
    'Syria',
    'Indonesia',
    'Sudan',
    'Syria Cross Border',
]


# used for user list view
class MinimalUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    email = serializers.EmailField(validators=[EmailValidator()])
    phone = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'name',
            'first_name',
            'middle_name',
            'last_name',
            'username',
            'email',
            'phone',
        )

    def get_phone(self, obj):
        if obj.profile:
            return obj.profile.phone_number
        return None


# used for user detail view
class MinimalUserDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    job_title = serializers.CharField(source='profile.job_title')
    vendor_number = serializers.CharField(source='profile.vendor_number')
    email = serializers.EmailField(validators=[EmailValidator()])

    class Meta:
        model = get_user_model()
        fields = ('name', 'first_name', 'middle_name', 'last_name', 'username', 'email', 'job_title', 'vendor_number',)


class CountrySerializer(serializers.ModelSerializer):
    local_currency = serializers.CharField(source='local_currency.name', read_only=True)

    class Meta:
        model = Country
        fields = (
            'id',
            'name',
            'latitude',
            'longitude',
            'initial_zoom',
            'local_currency',
            'custom_dashboards',
        )


class DashboardCountrySerializer(CountrySerializer):

    class Meta(CountrySerializer.Meta):
        fields = CountrySerializer.Meta.fields + ('custom_dashboards', )


class CountryDetailSerializer(serializers.ModelSerializer):
    local_currency = serializers.CharField(source='local_currency.name', read_only=True)
    local_currency_id = serializers.IntegerField(source='local_currency.id', read_only=True)
    local_currency_code = serializers.CharField(source='local_currency.code', read_only=True)

    class Meta:
        model = Country
        fields = (
            'id',
            'name',
            'latitude',
            'longitude',
            'initial_zoom',
            'local_currency',
            'local_currency_id',
            'local_currency_code',
            'business_area_code',
            'country_short_code',
        )


class RealmSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(source='group.id')
    group_name = serializers.CharField(source='group.name')

    class Meta:
        model = Realm
        fields = (
            'id',
            'group_id',
            'group_name',
            'is_active'
        )


class UserRealmRetrieveSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name')
    realms = RealmSerializer(many=True, read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'is_active',
            'last_login',
            'name',
            'email',
            'realms'
        )


class UserRealmCreateUpdateSerializer(
    DynamicFieldsSerializerMixin,
    GroupEditPermissionMixin,
    serializers.ModelSerializer
):
    job_title = serializers.CharField(required=False, write_only=True)
    organization = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    groups = serializers.ListField(child=serializers.IntegerField(), required=True, write_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'first_name',
            'last_name',
            'email',
            'job_title',
            'organization',
            'groups'
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate_organization(self, value):
        organization_id = value
        if organization_id:
            organization = get_object_or_404(Organization, pk=organization_id)
            if not self.context['request'].user.is_partnership_manager:
                raise ValidationError(
                    _('You do not have permissions to change groups for %(name)s organization.'
                      % {'name': organization.name}))
        return value

    def create(self, validated_data):
        organization_id = validated_data.pop("organization", None)
        if not organization_id:
            organization_id = self.context['request'].user.profile.organization.id
        group_ids = set(validated_data.pop("groups"))
        job_title = validated_data.pop("job_title")

        validated_data.update({"username": validated_data["email"]})
        instance = super().create(validated_data)

        if job_title:
            instance.profile.job_title = job_title
        instance.profile.country = connection.tenant
        instance.profile.organization_id = organization_id
        instance.profile.save(update_fields=['country', 'organization_id', 'job_title'])

        self.create_realms(instance, organization_id, group_ids)

        return instance

    def create_realms(self, instance, organization_id, group_ids):
        allowed_group_ids = set(self.get_user_allowed_groups(self.context['request'].user).values_list('id', flat=True))
        if not group_ids or not group_ids.issubset(allowed_group_ids):
            raise PermissionDenied(
                _('Permission denied. Only %(groups)s roles can be assigned.'
                  % {'groups': ', '.join(Group.objects.filter(id__in=allowed_group_ids).values_list('name', flat=True))})
            )
        Realm.objects.bulk_create([
            Realm(user=instance, country=connection.tenant, organization_id=organization_id, group_id=group_id)
            for group_id in group_ids])

    def update(self, instance, validated_data):
        organization = validated_data.get('organization', instance.profile.organization)
        requested_group_ids = set(validated_data.get('groups'))
        context_qs_params = {'country': connection.tenant, 'organization': organization}
        realm_qs = instance.realms.filter(**context_qs_params)

        if requested_group_ids == []:
            realm_qs.update(is_active=False)
            return

        # the group ids the authenticated user is allowed to update
        allowed_group_ids = set(self.get_user_allowed_groups(self.context['request'].user).values_list('id', flat=True))
        # the existing group ids of the user that are allowed to be updated
        existing_group_ids = set(instance.get_groups_for_organization(organization).filter(id__in=allowed_group_ids).values_list('id', flat=True))
        _to_add = requested_group_ids.difference(existing_group_ids)
        _to_deactivate = existing_group_ids.difference(requested_group_ids)
        _to_reactivate = requested_group_ids.difference(_to_add)

        if not allowed_group_ids or \
                not _to_add.issubset(allowed_group_ids) or \
                not _to_deactivate.issubset(allowed_group_ids) or \
                not _to_reactivate.issubset(allowed_group_ids):
            raise PermissionDenied(
                _('Permission denied. Only %(groups)s roles can be assigned.'
                  % {'groups': ', '.join(Group.objects.filter(id__in=allowed_group_ids).values_list('name', flat=True))})
            )
        Realm.objects.bulk_create([
            Realm(user=instance, country=connection.tenant, organization=organization, group_id=group_id)
            for group_id in _to_add])
        realm_qs.filter(group__id__in=_to_deactivate).update(is_active=False)
        realm_qs.filter(group__id__in=_to_reactivate).update(is_active=True)
        # clean up profile organization if no realm is active for context country and organization
        if not instance.realms.filter(is_active=True, **context_qs_params).count():
            instance.profile.organization = None
            instance.profile.save(update_fields=['organization'])

        return instance


class UserPreferencesSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=dict(LANGUAGES))


class ProfileRetrieveUpdateSerializer(serializers.ModelSerializer):
    countries_available = SimpleCountrySerializer(many=True, read_only=True)
    organizations_available = SimpleOrganizationSerializer(many=True, read_only=True)
    supervisor = serializers.PrimaryKeyRelatedField(read_only=True)
    groups = GroupSerializer(source="user.groups", read_only=True, many=True)
    supervisees = serializers.PrimaryKeyRelatedField(source='user.supervisee', many=True, read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True)
    is_superuser = serializers.BooleanField(source='user.is_superuser', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    middle_name = serializers.CharField(source='user.middle_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    is_staff = serializers.BooleanField(source='user.is_staff', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    country = DashboardCountrySerializer(read_only=True)
    organization = SimpleOrganizationSerializer(read_only=True)
    show_ap = serializers.SerializerMethodField()
    is_unicef_user = serializers.SerializerMethodField()
    _partner_staff_member = serializers.SerializerMethodField()

    preferences = UserPreferencesSerializer(source="user.preferences", allow_null=False)

    class Meta:
        model = UserProfile
        exclude = ('id', 'old_countries_available')

    # TODO remove once feature gating is in place.
    def get_show_ap(self, obj):
        """If user is within one of the allowed countries then
        show_ap is True, otherwise False
        """
        if obj.country and obj.country.name in AP_ALLOWED_COUNTRIES:
            return True
        return False

    def get__partner_staff_member(self, obj):
        psm = obj.user.get_partner_staff_member()
        return psm.id if psm else None

    def get_is_unicef_user(self, obj):
        return obj.user.is_unicef_user()

    def update(self, instance, validated_data):
        user = validated_data.pop('user', None)
        if user and user.get('preferences'):
            instance.user.preferences = user.get('preferences')
            instance.user.save(update_fields=['preferences'])
        return super().update(instance, validated_data)


class SimpleUserSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='profile.country', read_only=True)
    email = serializers.EmailField(validators=[EmailValidator()])

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'username',
            'email',
            'is_superuser',
            'first_name',
            'middle_name',
            'last_name',
            'is_staff',
            'is_active',
            'profile',
            'country',
        )


# TODO: user upper case validator here
class ExternalUserSerializer(MinimalUserSerializer):
    email = serializers.EmailField(
        label='Email Address',
        max_length=254,
        validators=[ExternalUserValidator()],
    )

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'name',
            'first_name',
            'middle_name',
            'last_name',
            'username',
            'email',
        )
        read_only_fields = ["username"]

    @staticmethod
    def _get_user_qs(data):
        return get_user_model().objects.filter(email=data.get("email"))

    @staticmethod
    def _get_external_psea_org():
        return Organization.objects.get(vendor_number='EXTERNAL PSEA ASSESSORS')

    def validate(self, data):
        data = super().validate(data)
        if not self.instance:
            user_qs = self._get_user_qs(data)
            if user_qs.exists():
                exists, __ = self._in_realm(user_qs.first())
                if exists:
                    raise serializers.ValidationError("User already exists.")
        return data

    def _in_realm(self, instance):
        country = Country.objects.get(schema_name=connection.schema_name)
        realm_qs = Realm.objects.filter(
            user=instance,
            country=country,
            organization=self._get_external_psea_org(),
            group=Auditor.as_group())
        if not realm_qs.exists():
            return False, country
        return True, country

    def _add_to_realm(self, instance):
        exists, country = self._in_realm(instance)
        if not exists:
            Realm.objects.create(
                user=instance,
                country=country,
                organization=self._get_external_psea_org(),
                group=Auditor.as_group(),
            )
        instance.profile.organization = self._get_external_psea_org()
        if instance.profile.countries_available.count() == 1:
            if (
                    not instance.profile.country_override and
                    country.schema_name.lower() not in ["uat", "public"]
            ):
                instance.profile.country_override = country
        instance.profile.save()

    def create(self, validated_data):
        validated_data["username"] = validated_data.get("email")
        # check if user record actually exists
        user_qs = self._get_user_qs(validated_data)
        if user_qs.exists():
            instance = user_qs.first()
        else:
            instance = super().create(validated_data)
        self._add_to_realm(instance)
        return instance
