from django.contrib.auth import get_user_model
from django.utils.encoding import force_str

from rest_framework import serializers

from etools.applications.organizations.models import Organization
from etools.applications.users.models import Country, Group, Realm, UserProfile
from etools.applications.users.validators import EmailValidator, LowerCaseEmailValidator


class SimpleCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name', 'business_area_code')


class SimpleOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name']


class OrganizationSerializer(SimpleOrganizationSerializer):
    """
    Used for the current organization only on user profile.
    Do not use this serializer on a list of Organizations due to performance issues.
    """
    relationship_types = serializers.ListSerializer(child=serializers.CharField(), read_only=True)

    class Meta(SimpleOrganizationSerializer.Meta):
        model = Organization
        fields = SimpleOrganizationSerializer.Meta.fields + ['relationship_types']


class UserProfileSerializer(serializers.ModelSerializer):

    office = serializers.CharField(
        source='tenant_profile.office.name',
        read_only=True,
    )
    country_name = serializers.CharField(source='country.name', read_only=True)
    countries_available = SimpleCountrySerializer(many=True, read_only=True)

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
        )


class UserManagementSerializer(serializers.Serializer):
    user_email = serializers.EmailField(
        required=True,
        validators=[LowerCaseEmailValidator()],
    )
    roles = serializers.ListSerializer(child=serializers.ChoiceField(choices=["Partnership Manager",
                                                                              "PME",
                                                                              "Travel Administrator",
                                                                              "UNICEF Audit Focal Point",
                                                                              "Travel Focal Point",
                                                                              "FM User",
                                                                              "Driver",
                                                                              "PRC Secretary"]), required=True)
    workspace = serializers.CharField(required=True)
    access_type = serializers.ChoiceField(choices=["grant", "revoke", "set"], required=True)


class SimpleProfileSerializer(serializers.ModelSerializer):

    user_id = serializers.CharField(source="user.id")
    email = serializers.EmailField(
        source="user.email",
        validators=[EmailValidator(), LowerCaseEmailValidator()],
    )
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    class Meta:
        model = UserProfile
        fields = (
            'user_id',
            'full_name',
            'username',
            'email'
        )


class SimpleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'id',
            'name',
        ]


class GroupSerializer(SimpleGroupSerializer):

    permissions = serializers.SerializerMethodField()

    def get_permissions(self, group):
        return [perm.id for perm in group.permissions.all()]

    def create(self, validated_data):
        try:
            group = Group.objects.create(**validated_data)

        except Exception as ex:
            raise serializers.ValidationError({'group': force_str(ex)})

        return group

    class Meta(SimpleGroupSerializer.Meta):
        model = Group
        fields = SimpleGroupSerializer.Meta.fields + ['permissions']


class ProfileRetrieveUpdateSerializer(serializers.ModelSerializer):
    countries_available = SimpleCountrySerializer(many=True, read_only=True)
    supervisor = serializers.CharField(read_only=True)
    groups = GroupSerializer(source="user.groups", read_only=True, many=True)
    supervisees = serializers.PrimaryKeyRelatedField(source='user.supervisee', many=True, read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    office = serializers.CharField(source="tenant_profile.office")

    class Meta:
        model = UserProfile
        fields = ('name', 'office', 'supervisor', 'countries_available',
                  'oic', 'groups', 'supervisees', 'job_title', 'phone_number')


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(source='get_full_name')
    groups = GroupSerializer(many=True)

    class Meta:
        model = get_user_model()
        exclude = ('password', 'user_permissions')


class UserProfileCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
        )


class SimpleNestedProfileSerializer(serializers.ModelSerializer):
    office = serializers.CharField(source="tenant_profile.office")

    class Meta:
        model = UserProfile
        fields = ('country', 'office')


class SimpleUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[EmailValidator(), LowerCaseEmailValidator()])
    profile = SimpleNestedProfileSerializer()

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
            'profile'
        )


class MinimalUserSerializer(SimpleUserSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'name', 'first_name', 'middle_name', 'last_name')


class UserCreationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    groups = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()
    profile = UserProfileCreationSerializer()
    email = serializers.EmailField(validators=[EmailValidator(), LowerCaseEmailValidator()])

    def get_groups(self, user):
        return [grp.id for grp in user.groups.all()]

    def get_user_permissions(self, user):
        return [perm.id for perm in user.user_permissions.all()]

    def create(self, validated_data):
        user_profile = validated_data.pop('profile', {})
        groups = validated_data.pop('groups', [])
        countries = user_profile.pop('countries_available', [])

        try:
            user = get_user_model().objects.create(**validated_data)
            user.profile.country = user_profile['country']
            user.profile.organization = user_profile['organization']
            user.profile.tenant_profile.office = user_profile['office']
            user.profile.job_title = user_profile['job_title']
            user.profile.phone_number = user_profile['phone_number']
            user.profile.country_override = user_profile['country_override']
            realm_list = []
            for country in countries:
                for group in groups:
                    realm_list.append(Realm(
                        user=user,
                        country=country,
                        organization=user.profile.organization,
                        group=group
                    ))
            Realm.objects.bulk_create(realm_list)
            user.save()
            user.profile.save()

        except Exception as ex:
            raise serializers.ValidationError({'user': force_str(ex)})

        return user

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
            'groups',
            'user_permissions',
            'profile',
            't2f',
        )


class CountrySerializer(SimpleUserSerializer):
    local_currency_code = serializers.CharField(source='local_currency', read_only=True)

    class Meta:
        model = Country
        fields = (
            'id',
            'name',
            'latitude',
            'longitude',
            'initial_zoom',
            'local_currency_code',
            'business_area_code',
            'country_short_code',
            'iso3_code',
            'schema_name',
        )


class PRPSyncRealmSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='country.id')
    organization = serializers.CharField(source='organization.vendor_number')
    group = serializers.CharField(source='group.name')

    class Meta:
        model = Realm
        fields = (
            'country',
            'organization',
            'group',
        )


class PRPSyncUserSerializer(serializers.ModelSerializer):
    realms = PRPSyncRealmSerializer(many=True)

    class Meta:
        model = get_user_model()
        fields = (
            'email',
            'realms',
        )
