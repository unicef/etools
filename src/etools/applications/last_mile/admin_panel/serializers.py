
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_str

from rest_framework import serializers
from rest_framework_gis.fields import GeometryField

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.constants import ALERT_TYPES, TRANSFER_MANUAL_CREATION_NAME
from etools.applications.last_mile.admin_panel.validators import AdminPanelValidator
from etools.applications.last_mile.permissions import LastMileUserPermissionRetriever
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
            'status',
        )


class UserProfileCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
            'country',
            'country_override',
        )


class UserAdminCreateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    profile = UserProfileCreationSerializer()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(validators=[EmailValidator(), LowerCaseEmailValidator()])
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

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


class ParentLocationsSerializer(serializers.Serializer):
    country = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True)
    district = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        location_data = {"country": None, "region": None, "district": None}
        parent_locations = instance.get_parent_locations()
        if instance.FIRST_ADMIN_LEVEL in parent_locations:
            location_data["country"] = parent_locations.get(instance.FIRST_ADMIN_LEVEL).name
        if instance.SECOND_ADMIN_LEVEL in parent_locations:
            location_data["region"] = parent_locations.get(instance.SECOND_ADMIN_LEVEL).name
        if instance.THIRD_ADMIN_LEVEL in parent_locations:
            location_data["district"] = parent_locations.get(instance.THIRD_ADMIN_LEVEL).name
        return location_data


class PointOfInterestAdminSerializer(serializers.ModelSerializer):
    partner_organizations = SimplePartnerOrganizationSerializer(many=True, read_only=True)
    poi_type = PointOfInterestTypeSerializer(read_only=True)
    country = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True)
    district = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        parent_locations = ParentLocationsSerializer(instance.parent).data
        data.update(parent_locations)
        return data

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
    country = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True)
    district = serializers.CharField(read_only=True)
    primary_type = serializers.SerializerMethodField()
    implementing_partner = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        parent_locations = ParentLocationsSerializer(instance.parent).data
        data.update(parent_locations)
        return data

    def get_primary_type(self, obj):
        return obj.poi_type.name if obj.poi_type else None

    def get_implementing_partner(self, obj):
        partners = obj.partner_organizations.all().prefetch_related('organization')
        return ",".join([f"{partner.organization.vendor_number} - {partner.organization.name}" if partner.organization else partner.name if partner.name else "-" for partner in partners])

    def get_lat(self, obj):
        return obj.point.y if obj.point else None

    def get_lng(self, obj):
        return obj.point.x if obj.point else None

    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name', 'primary_type', 'p_code', 'lat', 'lng', 'status', 'implementing_partner', 'region', 'district', 'country')
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
    points_of_interest = serializers.SerializerMethodField()

    def get_points_of_interest(self, obj):
        points = obj.points_of_interest.all().order_by('id')
        return PointOfInterestSerializer(points, many=True).data

    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name', 'vendor_number', 'points_of_interest')  # add any additional fields as needed


class UserPointOfInterestAdminSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    partners = PartnerSerializer(source='profile.organization.partner', read_only=True)
    last_name = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    point_of_interest = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=models.PointOfInterest.objects.all(),
        write_only=True
    )

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
        fields = ('id', 'original_uom', 'short_description', 'number')


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


class TransferItemDetailSerializer(serializers.Serializer):
    item_name = serializers.CharField(required=True)
    material = serializers.PrimaryKeyRelatedField(
        queryset=models.Material.objects.all(),
        required=True
    )
    quantity = serializers.IntegerField(required=True)
    uom = serializers.CharField(required=True)


class TransferItemCreateSerializer(serializers.ModelSerializer):

    partner_organization = serializers.PrimaryKeyRelatedField(
        queryset=PartnerOrganization.objects.all(),
        write_only=True,
        required=True
    )
    location = serializers.PrimaryKeyRelatedField(
        queryset=models.PointOfInterest.objects.all(),
        write_only=True,
        required=True
    )
    items = TransferItemDetailSerializer(many=True, write_only=True, required=True)

    adminValidator = AdminPanelValidator()

    @transaction.atomic
    def create(self, validated_data):
        self.adminValidator.validate_items(validated_data.get('items', []))
        self.adminValidator.validate_partner_location(validated_data.get('location'), validated_data.get('partner_organization'))
        items = validated_data.pop('items', [])
        validated_data['unicef_release_order'] = f"{TRANSFER_MANUAL_CREATION_NAME} {timezone.now().strftime('%d-%m-%Y %H:%M:%S')}"
        validated_data['transfer_type'] = models.Transfer.DELIVERY
        validated_data['destination_point'] = validated_data.pop('location')
        instance = models.Transfer.objects.create(
            **validated_data
        )
        items_to_create = []
        for item in items:
            items_to_create.append(
                models.Item(
                    transfer=instance,
                    material=item.get('material'),
                    quantity=item.get('quantity'),
                    uom=item.get('uom'),
                    batch_id=item.get('item_name'),
                )
            )
        models.Item.objects.bulk_create(items_to_create)
        return instance

    class Meta:
        model = models.Transfer
        fields = ('id', 'items', 'partner_organization', 'location')


class OrganizationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('name', 'vendor_number', 'id')


class LocationsAdminSerializer(serializers.ModelSerializer):
    country = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True)
    district = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        parent_locations = ParentLocationsSerializer(instance).data
        data.update(parent_locations)
        return data

    class Meta:
        model = Location
        fields = ('id', 'country', 'region', 'district')


class PointOfInterestTypeAdminSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    def validate_name(self, value):
        self.adminValidator.validate_poi_type(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        return models.PointOfInterestType.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance

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
    origin_point = serializers.SerializerMethodField()
    destination_point = serializers.SerializerMethodField()

    def get_origin_point(self, obj):
        return obj.origin_point.name if obj.origin_point else None

    def get_destination_point(self, obj):
        return obj.destination_point.name if obj.destination_point else None

    def get_from_partner_organization(self, obj):
        return obj.from_partner_organization.organization.name if obj.from_partner_organization else None

    def get_recipient_partner_organization(self, obj):
        return obj.recipient_partner_organization.organization.name if obj.recipient_partner_organization else None

    class Meta:
        model = models.Transfer
        fields = ('id', 'created', 'modified', 'unicef_release_order', 'name', 'transfer_type', 'transfer_subtype', 'status', 'origin_point', 'destination_point', 'from_partner_organization', 'recipient_partner_organization')


class TransferHistoryAdminSerializer(serializers.ModelSerializer):
    primary_transfer = serializers.SerializerMethodField()

    def get_primary_transfer(self, obj):
        return BaseTransferSerializer(obj.origin_transfer).data

    class Meta:
        model = models.TransferHistory
        fields = ('id', 'created', 'modified', 'primary_transfer')


class PartnerOrganizationAdminSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    vendor_number = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.organization.name if obj.organization else "-"

    def get_vendor_number(self, obj):
        return obj.organization.vendor_number if obj.organization else "-"

    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name', 'vendor_number')


class AuthUserPermissionsDetailSerializer(serializers.ModelSerializer):
    admin_perms = serializers.SerializerMethodField()

    def get_admin_perms(self, obj):
        return LastMileUserPermissionRetriever().get_permissions(obj)

    class Meta:
        model = get_user_model()
        fields = ('admin_perms',)
