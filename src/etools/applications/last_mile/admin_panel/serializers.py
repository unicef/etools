
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.encoding import force_str

from rest_framework import serializers
from rest_framework_gis.fields import GeometryField

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.constants import ALERT_TYPES
from etools.applications.last_mile.admin_panel.validators import AdminPanelValidator
from etools.applications.last_mile.serializers import PointOfInterestTypeSerializer
from etools.applications.locations.models import Location
from etools.applications.organizations.models import Organization
from etools.applications.partners.models import PartnerOrganization
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


class UserAdminExportSerializer(serializers.ModelSerializer):
    implementing_partner = serializers.SerializerMethodField(read_only=True)
    country = serializers.CharField(source='profile.country.name', read_only=True)
    status = serializers.SerializerMethodField(read_only=True)

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def get_implementing_partner(self, obj):
        return f"{obj.profile.organization.vendor_number if obj.profile.organization else '-'} - {obj.profile.organization.name if obj.profile.organization else '-'}"

    class Meta:
        model = get_user_model()
        fields = (
            'first_name',
            'last_name',
            'email',
            'implementing_partner',
            'country',
            'is_active',
            'last_login',
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
        validated_data['password'] = make_password(validated_data['password'])
        country_schema = self.context.get('country_schema')
        country = Country.objects.get(schema_name=country_schema)

        try:
            user = get_user_model().objects.create(**validated_data)
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


class PointOfInterestCustomSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
    )
    partner_organizations = serializers.PrimaryKeyRelatedField(
        queryset=PartnerOrganization.objects.all(),
        many=True,
    )
    poi_type = serializers.PrimaryKeyRelatedField(
        queryset=models.PointOfInterestType.objects.all(),
    )
    point = GeometryField(required=False)

    class Meta:
        model = models.PointOfInterest
        fields = ('name', 'parent', 'p_code', 'partner_organizations', 'poi_type', 'point')


class SimplePartnerOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name', 'vendor_number')


class PointOfInterestAdminSerializer(serializers.ModelSerializer):
    partner_organizations = SimplePartnerOrganizationSerializer(many=True, read_only=True)
    poi_type = PointOfInterestTypeSerializer(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
    region = serializers.SerializerMethodField(read_only=True)
    district = serializers.SerializerMethodField(read_only=True)

    def extract_location_info(self, location_obj):
        location_data = {"district": None, "region": None, "country": None}

        current = location_obj
        while current:
            admin_level = getattr(current, "admin_level_name", None)
            name = getattr(current, "name", None)

            if admin_level == "District":
                location_data["district"] = name
            elif admin_level == "Region":
                location_data["region"] = name
            elif admin_level == "Country":
                location_data["country"] = name

            current = getattr(current, "parent", None)

        return location_data

    def get_country(self, obj):
        return self.extract_location_info(obj).get('country')

    def get_region(self, obj):
        return self.extract_location_info(obj).get('region')

    def get_district(self, obj):
        return self.extract_location_info(obj).get('district')

    class Meta:
        model = models.PointOfInterest
        fields = '__all__'


class PointOfInterestListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        ret = []
        for poi in data:
            poi_data = self.child.to_representation(poi)
            partners = poi_data.pop('implementing_partner', [])
            if partners:
                partner_split = partners.split(",")
                for partner in partner_split:
                    poi_row = poi_data.copy()
                    poi_row['implementing_partner'] = partner
                    ret.append(poi_row)
            else:
                poi_data['implementing_partner'] = ""
                ret.append(poi_data)
        return ret


class PointOfInterestExportSerializer(serializers.ModelSerializer):
    state = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    primary_type = serializers.SerializerMethodField()
    implementing_partner = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def get_state(self, obj):
        return PointOfInterestAdminSerializer().extract_location_info(obj).get('country')

    def get_region(self, obj):
        return PointOfInterestAdminSerializer().extract_location_info(obj).get('region')

    def get_district(self, obj):
        return PointOfInterestAdminSerializer().extract_location_info(obj).get('district')

    def get_primary_type(self, obj):
        return obj.poi_type.name

    def get_implementing_partner(self, obj):
        partners = obj.partner_organizations.all()
        return ",".join([f"{partner.organization.vendor_number} - {partner.organization.name}" if partner.organization else partner.name if partner.name else "-" for partner in partners])

    def get_lat(self, obj):
        return obj.point.y if obj.point else None

    def get_lng(self, obj):
        return obj.point.x if obj.point else None

    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name', 'state', 'region', 'district', 'primary_type', 'p_code', 'lat', 'lng', 'status', 'implementing_partner')
        list_serializer_class = PointOfInterestListSerializer


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
        fields = ('id', 'name', 'vendor_number', 'points_of_interest')  # add any additional fields as needed


class UserPointOfInterestAdminSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    partners = PartnerSerializer(source='profile.organization.partner', read_only=True)
    point_of_interest = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=models.PointOfInterest.objects.all(),
        write_only=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['last_name', 'first_name', 'email']:
            self.fields[field].read_only = True

    @transaction.atomic
    def update(self, instance, validated_data):
        self.adminValidator.validate_profile(instance)
        poi_list = validated_data.pop('point_of_interest', None)
        if poi_list is not None:
            partner = instance.profile.organization.partner
            partner.points_of_interest.set(poi_list)
            instance.save()

        return instance

    class Meta:
        model = get_user_model()
        fields = ('id', 'last_name', 'first_name', 'email', 'partners', 'point_of_interest')


class UserPointOfInterestExportSerializer(serializers.ModelSerializer):

    location = serializers.SerializerMethodField()
    implementing_partner = serializers.SerializerMethodField()

    def get_implementing_partner(self, obj):
        return f"{obj.profile.organization.vendor_number if obj.profile.organization else '-'} - {obj.profile.organization.name if obj.profile.organization else '-'}"

    def get_location(self, obj):
        return ", ".join([location.name for location in obj.profile.organization.partner.points_of_interest.all()])

    class Meta:
        model = get_user_model()
        fields = ('id', 'first_name', 'last_name', 'email', 'implementing_partner', 'location')


class AlertNotificationSerializer(serializers.ModelSerializer):

    alert_type = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField(source='user.email')

    def get_alert_type(self, obj):
        return self.context.get('ALERT_TYPES').get(obj.group.name)

    class Meta:
        model = Realm
        fields = ('id', 'email', 'alert_type')


class AlertNotificationCreateSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    email = serializers.EmailField(source='user.email')
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
    )

    @transaction.atomic
    def create(self, validated_data):
        self.adminValidator.validate_input_data(validated_data)
        self.adminValidator.validate_user_email(validated_data['user']['email'])
        self.adminValidator.validate_group_name(validated_data['group'], self.context['ALERT_TYPES'].keys())
        country_schema = self.context.get('country_schema')
        user = get_user_model().objects.get(email=validated_data['user']['email'])
        country = Country.objects.get(schema_name=country_schema)
        self.adminValidator.validate_realm(user, country, validated_data['group'])
        instance = Realm.objects.create(
            user=user,
            country=country,
            organization=user.profile.organization,
            group=validated_data['group']
        )
        return instance

    class Meta:
        model = Realm
        fields = ('email', 'group')


class AlertNotificationCustomeSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
    )

    @transaction.atomic
    def update(self, instance, validated_data):
        self.adminValidator.validate_group_name(validated_data['group'], self.context['ALERT_TYPES'].keys())
        instance.group = validated_data['group']
        instance.save()
        return instance

    @transaction.atomic
    def delete(self, instance):
        instance.delete()

    class Meta:
        model = Realm
        fields = ('group', )


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


class LocationsAdminSerializer(serializers.ModelSerializer):
    country = serializers.SerializerMethodField(read_only=True)
    region = serializers.SerializerMethodField(read_only=True)
    district = serializers.SerializerMethodField(read_only=True)

    def get_country(self, obj):
        return PointOfInterestAdminSerializer().extract_location_info(obj).get('country')

    def get_region(self, obj):
        return PointOfInterestAdminSerializer().extract_location_info(obj).get('region')

    def get_district(self, obj):
        return PointOfInterestAdminSerializer().extract_location_info(obj).get('district')

    class Meta:
        model = Location
        fields = ('id', 'country', 'region', 'district')


class PointOfInterestTypeAdminSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    @transaction.atomic
    def create(self, validated_data):
        self.adminValidator.validate_poi_type(validated_data['name'])
        return models.PointOfInterestType.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        self.adminValidator.validate_poi_type(validated_data['name'])
        return models.PointOfInterestType.objects.update(**validated_data)

    class Meta:
        model = models.PointOfInterestType
        fields = '__all__'


class AlertTypeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return ALERT_TYPES.get(obj.name, obj.name)

    class Meta:
        model = Group
        fields = ('id', 'name')


class BaseTransferSerializer(serializers.ModelSerializer):
    partner_organization = serializers.CharField(source='partner_organization.name')
    origin_point = serializers.CharField(source='origin_point.name')
    destination_point = serializers.CharField(source='destination_point.name')

    class Meta:
        model = models.Transfer
        fields = ('unicef_release_order', 'name', 'transfer_type', 'status', 'partner_organization', 'destination_point', 'origin_point')


class TransferLogAdminSerializer(serializers.ModelSerializer):
    from_partner_organization = serializers.SerializerMethodField()
    recipient_partner_organization = serializers.SerializerMethodField()
    origin_point = serializers.CharField(source='origin_point.name')
    destination_point = serializers.CharField(source='destination_point.name')

    def get_from_partner_organization(self, obj):
        return obj.from_partner_organization.name if obj.from_partner_organization else None

    def get_recipient_partner_organization(self, obj):
        return obj.recipient_partner_organization.name if obj.recipient_partner_organization else None

    class Meta:
        model = models.Transfer
        fields = ('id', 'created', 'modified', 'unicef_release_order', 'name', 'transfer_type', 'transfer_subtype', 'status', 'origin_point', 'destination_point', 'from_partner_organization', 'recipient_partner_organization')


class TransferHistoryAdminSerializer(serializers.ModelSerializer):
    primary_transfer = serializers.SerializerMethodField()

    def get_primary_transfer(self, obj):
        return BaseTransferSerializer(models.Transfer.objects.filter(id=obj.origin_transfer_id).first()).data

    class Meta:
        model = models.TransferHistory
        fields = ('id', 'created', 'modified', 'primary_transfer')
