from django.conf.global_settings import LANGUAGES
from django.contrib.auth import get_user_model
from django.db import connection

from rest_framework import serializers

from etools.applications.audit.models import Auditor
from etools.applications.users.models import Country, UserProfile
from etools.applications.users.serializers import GroupSerializer, SimpleCountrySerializer
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

    class Meta:
        model = get_user_model()
        fields = ('id', 'name', 'first_name', 'middle_name', 'last_name', 'username', 'email', )


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


class UserPreferencesSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=dict(LANGUAGES))


class ProfileRetrieveUpdateSerializer(serializers.ModelSerializer):
    countries_available = SimpleCountrySerializer(many=True, read_only=True)

    supervisor = serializers.CharField(read_only=True)
    groups = GroupSerializer(source="user.groups", read_only=True, many=True)
    supervisees = serializers.PrimaryKeyRelatedField(source='user.supervisee', many=True, read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    last_login = serializers.CharField(source='user.last_login', read_only=True)
    is_superuser = serializers.CharField(source='user.is_superuser', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    middle_name = serializers.CharField(source='user.middle_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    is_staff = serializers.CharField(source='user.is_staff', read_only=True)
    is_active = serializers.CharField(source='user.is_active', read_only=True)
    country = DashboardCountrySerializer(read_only=True)
    show_ap = serializers.SerializerMethodField()
    is_unicef_user = serializers.SerializerMethodField()

    preferences = UserPreferencesSerializer(source="user.preferences", allow_null=False)

    class Meta:
        model = UserProfile
        exclude = ('id',)

    # TODO remove once feature gating is in place.
    def get_show_ap(self, obj):
        """If user is within one of the allowed countries then
        show_ap is True, otherwise False
        """
        if obj.country and obj.country.name in AP_ALLOWED_COUNTRIES:
            return True
        return False

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

    def _get_user_qs(self, data):
        return get_user_model().objects.filter(email=data.get("email"))

    def validate(self, data):
        data = super().validate(data)
        if not self.instance:
            user_qs = self._get_user_qs(data)
            if user_qs.exists():
                exists, __ = self._in_country(user_qs.first())
                if exists:
                    raise serializers.ValidationError("User already exists.")
        return data

    def _in_country(self, instance):
        country = Country.objects.get(schema_name=connection.schema_name)
        if country not in instance.profile.countries_available.all():
            return (False, country)
        return (True, country)

    def _add_to_country(self, instance):
        exists, country = self._in_country(instance)
        if not exists:
            instance.profile.countries_available.add(country)
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
        self._add_to_country(instance)
        instance.groups.add(Auditor.as_group())
        return instance
