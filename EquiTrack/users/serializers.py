
from __future__ import unicode_literals
from rest_framework import serializers

from t2f.serializers.user_data import T2FUserDataSerializer
from .models import User, UserProfile, Group, Office, Section, Country


class SimpleCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name', 'business_area_code')


# used for user detail view
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


# used for user list view
class MinimalUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'name', 'first_name', 'last_name', 'username', 'email')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class CountrySerializer(serializers.ModelSerializer):
    local_currency = serializers.CharField(source='local_currency.name')

    class Meta:
        model = Country
        fields = (
            'id',
            'name',
            'latitude',
            'longitude',
            'initial_zoom',
            'local_currency',
        )


class ProfileRetrieveUpdateSerializer(serializers.ModelSerializer):
    countries_available = SimpleCountrySerializer(many=True, read_only=True)
    supervisor = serializers.CharField(read_only=True)
    groups = GroupSerializer(source="user.groups", read_only=True, many=True)
    supervisees = serializers.PrimaryKeyRelatedField(source='user.supervisee', many=True, read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    t2f = T2FUserDataSerializer(source='user')
    last_login = serializers.CharField(source='user.last_login', read_only=True)
    is_superuser = serializers.CharField(source='user.is_superuser', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    is_staff = serializers.CharField(source='user.is_staff', read_only=True)
    is_active = serializers.CharField(source='user.is_active', read_only=True)
    country = CountrySerializer(read_only=True)


    class Meta:
        model = UserProfile
        exclude = ('id', )


# used for user list
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')

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


# used in agreements
class SimpleUserSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='profile.country', read_only=True)

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
            'country'
        )
