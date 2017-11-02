from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from rest_framework import serializers
from serializers import GroupSerializer, SimpleCountrySerializer

from t2f.serializers.user_data import T2FUserDataSerializer
from users.models import Country, UserProfile


# used for user list view
class MinimalUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'name', 'first_name', 'last_name', 'username', 'email', )


# used for user detail view
class MinimalUserDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    job_title = serializers.CharField(source='profile.job_title')
    vendor_number = serializers.CharField(source='profile.vendor_number')

    class Meta:
        model = get_user_model()
        fields = ('name', 'first_name', 'last_name', 'username', 'email', 'job_title', 'vendor_number',)


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
        exclude = ('id',)


class SimpleUserSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='profile.country', read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'username',
            'email',
            'is_superuser',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'profile',
            'country',
        )
