
from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.db import transaction

from rest_framework import serializers

from etools.applications.last_mile import models
from etools.applications.last_mile.serializers import PointOfInterestTypeSerializer
from etools.applications.organizations.models import Organization
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import PartnerOrganizationListSerializer
from etools.applications.users.models import Country, Group, Realm, UserProfile
from etools.applications.users.serializers import SimpleUserSerializer
from etools.applications.users.validators import EmailValidator, LowerCaseEmailValidator


class UserAdminSerializer(SimpleUserSerializer):
    ip_name = serializers.CharField(source='profile.organization.name', read_only=True)
    ip_number = serializers.CharField(source='profile.organization.vendor_number', read_only=True)
    organization_id = serializers.CharField(source='profile.organization.id', read_only=True)
    country = serializers.CharField(source='profile.country.name', read_only=True)
    country_id = serializers.CharField(source='profile.country.id', read_only=True)

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
            'country_id',
            'organization_id',
        )


class UserProfileCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
            'country',
        )


class UserAdminCreateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    profile = UserProfileCreationSerializer()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(validators=[EmailValidator(), LowerCaseEmailValidator()])

    @transaction.atomic
    def create(self, validated_data):
        user_profile = validated_data.pop('profile', {})
        group = Group.objects.get(name="IP LM Editor")
        password = validated_data.pop('password', None)
        country_schema = self.context.get('country_schema')
        country = Country.objects.get(schema_name=country_schema)

        try:
            user = get_user_model().objects.create(**validated_data)
            user.set_password(password)
            user.profile.country = country
            user.profile.organization = user_profile['organization']
            user.profile.job_title = user_profile['job_title']
            user.profile.phone_number = user_profile['phone_number']
            user.profile.country_override = user_profile['country_override']
            Realm.objects.create(
                user=user,
                country=user.profile.country,
                organization=user.profile.organization,
                group=group
            )
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
            'password',
            'profile',
        )


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
    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})

        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        country = Country.objects.get(schema_name=self.context.get('country_schema'))

        profile = getattr(instance, 'profile', None)
        if profile:
            if 'organization' in profile_data:
                profile.organization = profile_data.get('organization')
                Realm.objects.filter(user=instance, country=country).update(organization=profile_data.get('organization'))
            if 'country' in profile_data:
                profile.country = country
            profile.save()

        return instance


class PointOfInterestAdminSerializer(serializers.ModelSerializer):
    partner_organizations = PartnerOrganizationListSerializer(many=True, read_only=True)
    poi_type = PointOfInterestTypeSerializer(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
    region = serializers.SerializerMethodField(read_only=True)

    def get_country(self, obj):
        return str(obj.parent.parent.parent if obj.parent.parent else obj.parent if obj.parent else '')

    def get_region(self, obj):
        return obj.parent.name if hasattr(obj, 'parent') else ''

    class Meta:
        model = models.PointOfInterest
        fields = '__all__'


class SimplePointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name')


class PointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name', 'description')  # include the fields you need


class PartnerSerializer(serializers.ModelSerializer):
    # Nest the related points_of_interest
    points_of_interest = PointOfInterestSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name', 'points_of_interest')  # add any additional fields as needed


class UserPointOfInterestAdminSerializer(serializers.ModelSerializer):

    # profile = UserProfileSerializer(read_only=True)
    locations = PartnerSerializer(source='profile.organization.partner', read_only=True)
    ip_name = serializers.CharField(source='profile.organization.name', read_only=True)
    ip_number = serializers.CharField(source='profile.organization.vendor_number', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('email', 'ip_name', 'ip_number', 'locations',)


class AlertNotificationSerializer(serializers.ModelSerializer):

    alert_type = serializers.SerializerMethodField(read_only=True)

    def get_alert_type(self, obj):
        list_mapped_groups = []
        for group in obj.groups.all():
            if group.name in self.context['ALERT_TYPES']:
                list_mapped_groups.append(self.context['ALERT_TYPES'].get(group.name, group.name))
        return list_mapped_groups

    class Meta:
        model = get_user_model()
        fields = ('email', 'alert_type')


class MaterialAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Material
        fields = ('original_uom', 'short_description', 'number')


class ItemAdminSerializer(serializers.ModelSerializer):
    material = MaterialAdminSerializer()
    description = serializers.SerializerMethodField(read_only=True)

    def get_description(self, obj):
        return obj.description

    class Meta:
        model = models.Item
        fields = ('material', 'quantity', 'modified', 'uom', 'batch_id', 'description')


class TransferItemSerializer(serializers.ModelSerializer):
    items = ItemAdminSerializer(many=True, read_only=True)
    destination_point = SimplePointOfInterestSerializer(read_only=True)
    origin_point = SimplePointOfInterestSerializer(read_only=True)

    class Meta:
        model = models.Transfer
        fields = ('items', 'destination_point', 'origin_point')


class OrganizationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('name', 'vendor_number', 'id')
