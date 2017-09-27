from rest_framework import serializers

from t2f.serializers.user_data import T2FUserDataSerializer
from users.models import User, UserProfile, Group, Office, Section, Country


class SimpleCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name', 'business_area_code')


class UserProfileSerializer(serializers.ModelSerializer):

    office = serializers.CharField(source='office.name')
    section = serializers.CharField(source='section.name')
    country_name = serializers.CharField(source='country.name')
    countries_available = SimpleCountrySerializer(many=True, read_only=True)

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
        )


class SimpleProfileSerializer(serializers.ModelSerializer):

    user_id = serializers.CharField(source="user.id")
    email = serializers.CharField(source="user.email")
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


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class ProfileRetrieveUpdateSerializer(serializers.ModelSerializer):
    countries_available = SimpleCountrySerializer(many=True, read_only=True)
    supervisor = serializers.CharField(read_only=True)
    groups = GroupSerializer(source="user.groups", read_only=True, many=True)
    supervisees = serializers.PrimaryKeyRelatedField(source='user.supervisee', many=True, read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ('name', 'office', 'section', 'supervisor', 'countries_available',
                  'oic', 'groups', 'supervisees', 'job_title', 'phone_number')


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(source='get_full_name')
    t2f = T2FUserDataSerializer(source='*')
    groups = GroupSerializer(many=True)

    class Meta:
        model = User
        exclude = ('password', 'groups', 'user_permissions')


class SectionSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Section
        fields = (
            'id',
            'name'
        )


class UserProfileCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
        )


class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, group):
        return [perm.id for perm in group.permissions.all()]

    def create(self, validated_data):
        try:
            group = Group.objects.create(**validated_data)

        except Exception as ex:
            raise serializers.ValidationError({'group': ex.message})

        return group

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            'permissions'
        )


class SimpleNestedProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            'country',
        )


class SimpleUserSerializer(serializers.ModelSerializer):
    profile = SimpleNestedProfileSerializer()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'is_superuser',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'profile'
        )


class MinimalUserSerializer(SimpleUserSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'name', 'first_name', 'last_name')


class UserCreationSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    groups = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()
    profile = UserProfileCreationSerializer()
    t2f = T2FUserDataSerializer(source='*', read_only=True)

    def get_groups(self, user):
        return [grp.id for grp in user.groups.all()]

    def get_user_permissions(self, user):
        return [perm.id for perm in user.user_permissions.all()]

    def create(self, validated_data):
        try:
            user_profile = validated_data.pop('profile')
        except KeyError:
            user_profile = {}

        try:
            countries = user_profile.pop('countries_available')
        except KeyError:
            countries = []

        try:
            user = User.objects.create(**validated_data)
            user.profile.country = user_profile['country']
            user.profile.office = user_profile['office']
            user.profile.section = user_profile['section']
            user.profile.partner_staff_member = 0
            user.profile.job_title = user_profile['job_title']
            user.profile.phone_number = user_profile['phone_number']
            user.profile.country_override = user_profile['country_override']
            user.profile.installation_id = user_profile['installation_id']
            for country in countries:
                user.profile.countries_available.add(country)

            user.save()
            user.profile.save()

        except Exception as ex:
            raise serializers.ValidationError({'user': ex.message})

        return user

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'is_superuser',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'groups',
            'user_permissions',
            'profile',
            't2f',
        )


class CountrySerializer(SimpleUserSerializer):
    local_currency_id = serializers.IntegerField(source='local_currency.id', read_only=True)

    class Meta:
        model = Country
        fields = (
            'name',
            'latitude',
            'longitude',
            'initial_zoom',
            'local_currency_id'
        )
