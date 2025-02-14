
from rest_framework import serializers
from etools.applications.partners.serializers.partner_organization_v2 import (
    PartnerOrganizationListSerializer,
)
from etools.applications.last_mile.serializers import PointOfInterestTypeSerializer
from etools.applications.last_mile import models
from django.contrib.auth import get_user_model
from etools.applications.users.serializers import SimpleUserSerializer


from etools.applications.organizations.models import Organization
from etools.applications.users.models import Country, UserProfile


class UserAdminSerializer(SimpleUserSerializer):
    ip_name = serializers.CharField(source='profile.organization.name', read_only=True)
    ip_number = serializers.CharField(source='profile.organization.vendor_number', read_only=True)
    country = serializers.CharField(source='profile.country.name', read_only=True)
    
    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'last_login',
            'ip_name',
            'ip_number',
            'country',
        )

class UserAdminCreateSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        source='profile.organization'
    )
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        source='profile.country'
    )
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = get_user_model()
        # Adjust the fields as needed.
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'password',
            'username',
            'organization',
            'country',
        )
    
    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password')
        
        user = get_user_model().objects.create(**validated_data)
        user.set_password(password)
        user.save()
        
        profile = getattr(user, 'profile', None)
        if profile:
            organization = profile_data.get('organization')
            country = profile_data.get('country')
            if organization:
                profile.organization = organization
            if country:
                profile.country = country
            profile.save()
        else:
            UserProfile.objects.create(user=user, **profile_data)
        
        return user
    
class UserAdminUpdateSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        source='profile.organization',
        required=False
    )
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        source='profile.country',
        required=False
    )
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = get_user_model()
        fields = (
            'email',
            'first_name',
            'last_name',
            'is_active',
            'password',
            'organization',
            'country',
        )
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        profile = getattr(instance, 'profile', None)
        if profile:
            if 'organization' in profile_data:
                profile.organization = profile_data.get('organization')
            if 'country' in profile_data:
                profile.country = profile_data.get('country')
            profile.save()
        
        return instance


class PointOfInterestAdminSerializer(serializers.ModelSerializer):
    partner_organizations = PartnerOrganizationListSerializer(many=True, read_only=True)
    poi_type = PointOfInterestTypeSerializer(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
    region = serializers.SerializerMethodField(read_only=True)

    def get_country(self, obj):
        # TODO: this will not work on multi country tenants . Not sure we need it at all
        # Need to to a logic to determine de country, region and so on
        return str(obj.parent.parent.parent if obj.parent.parent else obj.parent.parent)

    def get_region(self, obj):
        return obj.parent.name if hasattr(obj, 'parent') else ''

    class Meta:
        model = models.PointOfInterest
        fields = '__all__'
