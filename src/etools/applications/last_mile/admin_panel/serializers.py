from collections import defaultdict

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.db import connection, transaction
from django.utils.encoding import force_str

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_gis.fields import GeometryField

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.constants import (
    ALERT_TYPES,
    L_CONSIGNEE_ALREADY_EXISTS,
    REQUIRED_SECONDARY_TYPE,
    STOCK_EXISTS_UNDER_LOCATION,
)
from etools.applications.last_mile.admin_panel.services.lm_profile_status_updater import LMProfileStatusUpdater
from etools.applications.last_mile.admin_panel.services.lm_user_creator import LMUserCreator
from etools.applications.last_mile.admin_panel.services.reverse_transfer import ReverseTransfer
from etools.applications.last_mile.admin_panel.services.stock_management_create import StockManagementCreateService
from etools.applications.last_mile.admin_panel.services.transfer_approval import TransferApprovalService
from etools.applications.last_mile.admin_panel.validators import AdminPanelValidator
from etools.applications.last_mile.permissions import LastMileUserPermissionRetriever
from etools.applications.last_mile.serializers import PointOfInterestTypeSerializer
from etools.applications.locations.models import Location
from etools.applications.organizations.models import Organization
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import Country, Group, Realm, UserProfile
from etools.applications.users.serializers import MinimalUserSerializer, SimpleUserSerializer
from etools.applications.users.validators import EmailValidator, LowerCaseEmailValidator


class SimplePointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name')


class LastMileProfileSerializer(serializers.ModelSerializer):
    created_by = MinimalUserSerializer(read_only=True)
    approved_by = MinimalUserSerializer(read_only=True)
    user = MinimalUserSerializer(read_only=True)

    class Meta:
        model = models.Profile
        fields = ('id', 'user', 'status', 'created_by', 'approved_by', 'created_on', 'approved_on', 'review_notes')


class SimpleRealmSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='group.name', read_only=True)
    id = serializers.CharField(source='group.id', read_only=True)

    class Meta:
        model = Realm
        fields = ('id', 'name')


class UserAdminSerializer(SimpleUserSerializer):
    ip_name = serializers.CharField(source='profile.organization.name', read_only=True)
    ip_number = serializers.CharField(source='profile.organization.vendor_number', read_only=True)
    organization_id = serializers.CharField(source='profile.organization.id', read_only=True)
    country = serializers.CharField(source='profile.country.name', read_only=True)
    country_id = serializers.CharField(source='profile.country.id', read_only=True)
    last_mile_profile = serializers.CharField(source='profile.id', read_only=True)
    point_of_interests = serializers.SerializerMethodField(read_only=True)
    last_mile_profile = LastMileProfileSerializer(read_only=True)
    alert_types = serializers.SerializerMethodField(read_only=True)

    def get_alert_types(self, obj):
        realms = getattr(obj, 'realms', [])
        return SimpleRealmSerializer(realms, many=True, read_only=True).data

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
            'last_login',
            'organization_id',
            'point_of_interests',
            'last_mile_profile',
            'alert_types',
        )

    def get_point_of_interests(self, obj):
        poi_instances = [upoi.point_of_interest for upoi in obj.points_of_interest.all().order_by('id')]
        return SimplePointOfInterestSerializer(poi_instances, many=True, read_only=True).data


class UserAdminExportSerializer(serializers.ModelSerializer):
    implementing_partner = serializers.SerializerMethodField(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def get_country(self, obj):
        return connection.tenant.name

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
    email = serializers.EmailField(validators=[EmailValidator(), LowerCaseEmailValidator()])
    is_active = serializers.BooleanField(read_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    point_of_interests = serializers.PrimaryKeyRelatedField(many=True,
                                                            queryset=models.PointOfInterest.objects.all(),
                                                            write_only=True,
                                                            required=False,
                                                            allow_empty=True,
                                                            )
    last_mile_profile = LastMileProfileSerializer(read_only=True)

    def create(self, validated_data):
        validated_data['country_schema'] = self.context.get('country_schema')
        validated_data['created_by'] = self.context['request'].user
        try:
            user = LMUserCreator().create(validated_data)
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
            'profile',
            'point_of_interests',
            'last_mile_profile',
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['point_of_interests'] = []
        if (hasattr(instance.profile, 'organization') and instance.profile.organization and hasattr(instance.profile.organization, 'partner') and instance.profile.organization.partner):
            data['point_of_interests'] = [poi.id for poi in instance.profile.organization.partner.points_of_interest.all()]
        return data


class UserAdminUpdateSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

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
    point_of_interests = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=models.PointOfInterest.objects.all(),
        write_only=True,
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
            'point_of_interests',
        )

    def _validate_pois_for_user(self, user, points_of_interest, updated_partner=None):
        if not updated_partner:
            updated_partner = user.profile.organization.partner if user.profile.organization else None

        allowed_poi_ids = set()
        if updated_partner:
            partner_poi_ids = updated_partner.points_of_interest.values_list('id', flat=True)
            allowed_poi_ids.update(partner_poi_ids)

        global_poi_ids = models.PointOfInterest.objects.filter(
            partner_organizations__isnull=True, is_active=True
        ).exclude(name="UNICEF Warehouse").values_list('id', flat=True)
        allowed_poi_ids.update(global_poi_ids)
        new_poi_ids = {poi.id for poi in points_of_interest}

        if not new_poi_ids.issubset(allowed_poi_ids):
            invalid_ids = new_poi_ids - allowed_poi_ids
            invalid_pois = models.PointOfInterest.objects.filter(id__in=invalid_ids)
            invalid_names = ", ".join([poi.name for poi in invalid_pois])
            raise ValidationError(
                f'User does not have access to the following Points of Interest: {invalid_names}s'
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        self.adminValidator.validate_profile(instance)

        profile_data = validated_data.pop('profile', {})

        if 'point_of_interests' in validated_data:
            point_of_interests = validated_data.pop('point_of_interests')
            organization = profile_data.get('organization')
            self._validate_pois_for_user(instance, point_of_interests, getattr(organization, 'partner', None))
            new_poi_ids = {poi.id for poi in point_of_interests}
            models.UserPointsOfInterest.objects.filter(user=instance).exclude(
                point_of_interest_id__in=new_poi_ids
            ).delete()
            existing_poi_ids = set(
                models.UserPointsOfInterest.objects.filter(
                    user=instance
                ).values_list('point_of_interest_id', flat=True)
            )
            ids_to_create = new_poi_ids - existing_poi_ids
            if ids_to_create:
                new_relations = [
                    models.UserPointsOfInterest(user=instance, point_of_interest_id=poi_id)
                    for poi_id in ids_to_create
                ]
                models.UserPointsOfInterest.objects.bulk_create(new_relations)
        else:
            models.UserPointsOfInterest.objects.filter(user=instance).delete()

        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        country = Country.objects.get(schema_name=self.context.get('country_schema'))

        profile = getattr(instance, 'profile', None)
        old_organization = profile.organization if profile else None
        if profile and old_organization:
            if 'organization' in profile_data and profile.organization != profile_data.get('organization'):
                profile.organization = profile_data.get('organization')
                if not Realm.objects.filter(user=instance, country=country, organization=profile_data.get('organization')).exists():
                    Realm.objects.filter(user=instance, country=country, organization=old_organization).update(organization=profile_data.get('organization'))
            if 'country' in profile_data:
                profile.country = country
            profile.save()

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['point_of_interests'] = []
        if (hasattr(instance.profile, 'organization') and instance.profile.organization and hasattr(instance.profile.organization, 'partner') and instance.profile.organization.partner):
            data['point_of_interests'] = [poi.id for poi in instance.profile.organization.partner.points_of_interest.all()]
        return data


class PointOfInterestCustomSerializer(serializers.ModelSerializer):
    partner_organizations = serializers.PrimaryKeyRelatedField(
        queryset=PartnerOrganization.objects.all(),
        many=True,
    )
    poi_type = serializers.PrimaryKeyRelatedField(
        queryset=models.PointOfInterestType.objects.all(),
    )

    secondary_type = serializers.PrimaryKeyRelatedField(
        queryset=models.PointOfInterestType.objects.all(),
        required=False,
        allow_empty=True,
        allow_null=True
    )

    point = GeometryField(required=False)

    created_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    is_active = serializers.BooleanField(
        default=False
    )

    p_code = serializers.CharField(
        required=False,
        allow_null=True,
    )

    l_consignee_code = serializers.CharField(
        required=False,
        allow_null=True,
    )

    def validate_secondary_type(self, value):
        if not self.instance and not value:
            raise ValidationError(REQUIRED_SECONDARY_TYPE)
        return value

    def validate_l_consignee_code(self, value):
        if models.PointOfInterest.all_objects.filter(l_consignee_code=value).exists():
            raise ValidationError(L_CONSIGNEE_ALREADY_EXISTS)
        return value

    def validate_is_active(self, value):
        if self.instance and not value and self.instance.is_active:
            has_stock = models.Item.objects.filter(
                transfer__destination_point=self.instance,
                hidden=False
            ).exists()

            if has_stock:
                raise ValidationError(STOCK_EXISTS_UNDER_LOCATION)
        return value

    def validate(self, attrs):
        poi_type = attrs.get('poi_type')
        secondary_type = attrs.get('secondary_type')

        if poi_type and secondary_type:
            allowed_secondary_ids = models.PointOfInterestTypeMapping.get_allowed_secondary_types(poi_type.id)

            if allowed_secondary_ids and secondary_type.id not in allowed_secondary_ids:
                raise ValidationError({
                    'secondary_type': f"'{secondary_type.name}' is not a valid secondary type for primary type '{poi_type.name}'."
                })

        return super().validate(attrs)

    class Meta:
        model = models.PointOfInterest
        fields = ('name', 'partner_organizations', 'poi_type', 'secondary_type', 'point', 'created_by', 'is_active', 'p_code', 'l_consignee_code')


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


class ValidateBorderSerializer(serializers.Serializer):
    point = GeometryField(required=True)


class LocationBorderResponseSerializer(serializers.Serializer):
    def to_representation(self, instance):
        parent_locations = instance.get_parent_locations()

        data = {"valid": True}

        if instance.FIRST_ADMIN_LEVEL in parent_locations:
            loc = parent_locations[instance.FIRST_ADMIN_LEVEL]
            data["country"] = {
                "location": loc.name,
                "borders": loc.get_borders(tolerance=0.01) if loc.geom else []
            }

        if instance.SECOND_ADMIN_LEVEL in parent_locations:
            loc = parent_locations[instance.SECOND_ADMIN_LEVEL]
            data["region"] = {
                "location": loc.name,
                "borders": loc.get_borders(tolerance=0.01) if loc.geom else []
            }

        if instance.THIRD_ADMIN_LEVEL in parent_locations:
            loc = parent_locations[instance.THIRD_ADMIN_LEVEL]
            data["district"] = {
                "location": loc.name,
                "borders": loc.get_borders(tolerance=0.01) if loc.geom else []
            }

        if instance.FOURTH_ADMIN_LEVEL in parent_locations:
            loc = parent_locations[instance.FOURTH_ADMIN_LEVEL]
            data["subdistrict"] = {
                "location": loc.name,
                "borders": loc.get_borders(tolerance=0.01) if loc.geom else []
            }

        return data


class PointOfInterestAdminSerializer(serializers.ModelSerializer):
    partner_organizations = SimplePartnerOrganizationSerializer(many=True, read_only=True)
    poi_type = PointOfInterestTypeSerializer(read_only=True)
    secondary_type = PointOfInterestTypeSerializer(read_only=True)
    country = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True)
    district = serializers.CharField(read_only=True)
    pending_approval = serializers.SerializerMethodField(read_only=True)
    approved = serializers.SerializerMethodField(read_only=True)

    def get_pending_approval(self, obj):
        if hasattr(obj, 'pending_approval') and obj.pending_approval is not None:
            return obj.pending_approval
        return 0

    def get_approved(self, obj):
        if hasattr(obj, 'approved') and obj.approved is not None:
            return obj.approved
        return 0

    def to_representation(self, instance):
        data = super().to_representation(instance)
        parent_locations = ParentLocationsSerializer(instance.parent).data
        data.update(parent_locations)
        return data

    class Meta:
        model = models.PointOfInterest
        fields = '__all__'


class PointOfInterestWithCoordinatesSerializer(PointOfInterestAdminSerializer):

    borders = serializers.SerializerMethodField(read_only=True)

    def get_borders(self, obj):
        return PointOfInterestCoordinateAdminSerializer(obj).data


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


class POIExportListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        iterable = data.all() if hasattr(data, "all") else data
        rows = []
        for obj in iterable:
            rows.extend(self.child.generate_rows(obj))
        return rows


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

    def get_primary_type(self, obj):
        return obj.poi_type.name if obj.poi_type else None

    def get_implementing_partner(self, obj):
        partners = obj.partner_organizations.all().prefetch_related('organization')
        return ",".join([f"{partner.organization.vendor_number} - {partner.organization.name}" if partner.organization else partner.name if partner.name else "-" for partner in partners])

    def get_lat(self, obj):
        return obj.point.y if obj.point else None

    def get_lng(self, obj):
        return obj.point.x if obj.point else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        partners = instance.partner_organizations.all().prefetch_related('organization')
        implementing_partner_names = ",".join([f"{partner.organization.name}" if partner.organization else partner.name if partner.name else "-" for partner in partners])
        implementing_partner_numbers = ",".join([f"{partner.organization.vendor_number}" if partner.organization else partner.name if partner.name else "-" for partner in partners])
        data.update({
            "implementing_partner_names": implementing_partner_names,
            "implementing_partner_numbers": implementing_partner_numbers
        })
        if instance.parent:
            parent_locations = ParentLocationsSerializer(instance.parent).data
            data.update(parent_locations)
        return data

    def base_representation(self, instance):
        return self.to_representation(instance)

    def generate_rows(self, instance):
        base = self.base_representation(instance)
        transfers = (
            models.Transfer.all_objects
            .filter(destination_point=instance)
            .prefetch_related('items')
        )

        rows = []
        for transfer in transfers:
            for item in transfer.items.all():
                row = dict(base)
                row.update({
                    "transfer_name": transfer.name,
                    "transfer_ref": getattr(transfer, "unicef_release_order", None),
                    "item_id": item.id,
                    "item_name": getattr(item, "description", None),
                    "item_qty": getattr(item, "quantity", None),
                    "item_batch_number": getattr(item, "batch_id", None),
                    "item_expiry_date": getattr(item, "expiry_date", None),
                    'approval_status': transfer.approval_status,
                })
                rows.append(row)

        return rows or [base]

    @classmethod
    def bulk_generate_rows(cls, instances):
        poi_ids = [poi.id for poi in instances]

        transfers_qs = (
            models.Transfer.all_objects
            .filter(destination_point_id__in=poi_ids)
            .select_related('destination_point')
            .prefetch_related('items')
        )

        transfers_by_poi = defaultdict(list)
        for transfer in transfers_qs:
            transfers_by_poi[transfer.destination_point_id].append(transfer)

        all_rows = []
        serializer = cls()

        for instance in instances:
            base = serializer.base_representation(instance)
            poi_transfers = transfers_by_poi.get(instance.id, [])

            if poi_transfers:
                for transfer in poi_transfers:
                    for item in transfer.items.all():
                        row = dict(base)
                        row.update({
                            "transfer_name": transfer.name,
                            "transfer_ref": getattr(transfer, "unicef_release_order", None),
                            "item_id": item.id,
                            "item_name": getattr(item, "description", None),
                            "item_qty": getattr(item, "quantity", None),
                            "item_batch_number": getattr(item, "batch_id", None),
                            "item_expiry_date": getattr(item, "expiry_date", None),
                            'approval_status': transfer.approval_status,
                        })
                        all_rows.append(row)
            else:
                all_rows.append(base)

        return all_rows

    class Meta:
        model = models.PointOfInterest
        fields = (
            'id', 'name', 'primary_type', 'p_code', 'lat', 'lng',
            'status', 'implementing_partner', 'region', 'district', 'country',
        )
        list_serializer_class = POIExportListSerializer


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
        if (obj.profile and obj.profile.organization and obj.profile.organization.partner):
            return ", ".join([location.name for location in obj.profile.organization.partner.points_of_interest.all()])
        return ""

    class Meta:
        model = get_user_model()
        fields = ('id', 'first_name', 'last_name', 'email', 'implementing_partner', 'location')


class PointOfInterestLightSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        parent_locations = ParentLocationsSerializer(instance.parent).data
        data.update(parent_locations)
        return data

    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name', "point")


class UserAlertNotificationsExportSerializer(serializers.ModelSerializer):

    alert_types = serializers.SerializerMethodField(read_only=True)

    def get_alert_types(self, obj):
        alert_notifications = ""

        realms = obj.realms.all() if hasattr(obj, 'realms') else []

        for realm in realms:
            if realm.group:
                alert_notifications += f"{ALERT_TYPES.get(realm.group.name, realm.group.name)},"

        return alert_notifications

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'alert_types')


class AlertNotificationSerializer(serializers.ModelSerializer):

    alert_types = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField()

    def get_alert_types(self, obj):
        data = []

        realms = obj.realms.all() if hasattr(obj, 'realms') else []

        for realm in realms:
            if realm.group:
                data.append({
                    "id": realm.group.id,
                    "name": ALERT_TYPES.get(realm.group.name, realm.group.name)
                })

        return data

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'alert_types')


class AlertNotificationCreateSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    email = serializers.EmailField(source='user.email')
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True
    )

    @transaction.atomic
    def create(self, validated_data):
        self.adminValidator.validate_input_data(validated_data)
        self.adminValidator.validate_user_email(validated_data['user']['email'])
        self.adminValidator.validate_group_names(validated_data['groups'], self.context['ALERT_TYPES'].keys())
        country_schema = self.context.get('country_schema')
        user = get_user_model().objects.get(email=validated_data['user']['email'])
        old_realms = Realm.objects.filter(user=user, country__schema_name=country_schema, group__name__in=self.context['ALERT_TYPES'].keys())
        old_realms.delete()
        country = Country.objects.get(schema_name=country_schema)
        self.adminValidator.validate_realm(user, country, validated_data['groups'])
        realms_to_create = []
        for group in validated_data['groups']:
            realms_to_create.append(Realm(user=user, country=country, organization=user.profile.organization, group=group))
        Realm.objects.bulk_create(realms_to_create)
        return {
            "user": {"email": validated_data['user']['email']},
            'groups': [group for group in validated_data['groups']]
        }

    class Meta:
        model = Realm
        fields = ('email', 'groups')


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
        fields = ('id', 'original_uom', 'short_description', 'number', 'other')


class ItemAdminSerializer(serializers.ModelSerializer):
    material = MaterialAdminSerializer()
    description = serializers.SerializerMethodField(read_only=True)

    def get_description(self, obj):
        return obj.description

    class Meta:
        model = models.Item
        fields = ('material', 'quantity', 'modified', 'uom', 'batch_id', 'description')


class ItemStockManagementUpdateSerializer(serializers.ModelSerializer):

    adminValidator = AdminPanelValidator()

    def validate_uom(self, value):
        material = self.instance.material
        self.adminValidator.validate_uom_map(material, value)
        self.adminValidator.validate_uom(value)
        return value

    def validate_quantity(self, value):
        self.adminValidator.validate_positive_quantity(value)
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        if validated_data.get('quantity') and validated_data.get('quantity') != instance.quantity:
            instance.quantity = validated_data['quantity']
        if validated_data.get('uom') and validated_data.get('uom') != instance.uom:
            instance.uom = validated_data['uom']
        instance.save()
        return instance

    class Meta:
        model = models.Item
        fields = ('quantity', 'uom')


class ItemTransferAdminSerializer(serializers.ModelSerializer):
    material = MaterialAdminSerializer()
    description = serializers.SerializerMethodField(read_only=True)
    transfer_name = serializers.SerializerMethodField(read_only=True)
    approval_status = serializers.SerializerMethodField(read_only=True)

    def get_transfer_name(self, obj):
        if not obj.transfer:
            return None
        return obj.transfer.name or obj.transfer.unicef_release_order

    def get_description(self, obj):
        return obj.description

    def get_approval_status(self, obj):
        return obj.transfer.approval_status if obj.transfer else "REJECTED"

    class Meta:
        model = models.Item
        fields = ('id', 'material', 'quantity', 'modified', 'uom', 'batch_id', 'description', "transfer_name", "base_uom", "base_quantity", "expiry_date", "approval_status")


class TransferItemSerializer(serializers.ModelSerializer):
    items = ItemAdminSerializer(many=True, read_only=True)
    destination_point = SimplePointOfInterestSerializer(read_only=True)
    origin_point = SimplePointOfInterestSerializer(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = models.Transfer
        fields = ('items', 'destination_point', 'origin_point', 'status')


class TransferItemDetailSerializer(serializers.Serializer):
    item_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    material = serializers.PrimaryKeyRelatedField(
        queryset=models.Material.objects.all(),
        required=True
    )
    quantity = serializers.IntegerField(required=True)
    uom = serializers.CharField(required=True)
    expiry_date = serializers.DateField(allow_null=True, required=False)


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
        validated_data['created_by'] = self.context['request'].user
        return StockManagementCreateService().create_stock_management(validated_data)

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
    destination_point = serializers.SerializerMethodField()

    def get_destination_point(self, obj):
        return obj.destination_point.name if obj.destination_point else None

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
        if obj.from_partner_organization:
            return obj.from_partner_organization.organization.name
        return obj.partner_organization.organization.name if obj.partner_organization else None

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


class LocationWithBordersSerializer(serializers.Serializer):
    location = serializers.CharField(source='name')
    borders = serializers.SerializerMethodField()

    def get_borders(self, obj):
        return obj.get_borders()


class PointOfInterestCoordinateAdminSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        parent_locations = instance.parent.get_parent_locations()
        if instance.parent.FIRST_ADMIN_LEVEL in parent_locations:
            data['country'] = LocationWithBordersSerializer(parent_locations[instance.parent.FIRST_ADMIN_LEVEL]).data
        if instance.parent.SECOND_ADMIN_LEVEL in parent_locations:
            data['region'] = LocationWithBordersSerializer(parent_locations[instance.parent.SECOND_ADMIN_LEVEL]).data
        if instance.parent.THIRD_ADMIN_LEVEL in parent_locations:
            data['district'] = LocationWithBordersSerializer(parent_locations[instance.parent.THIRD_ADMIN_LEVEL]).data
        return data

    class Meta:
        model = models.PointOfInterest
        fields = ('id',)


class LastMileUserProfileUpdateAdminSerializer(serializers.ModelSerializer):

    admin_validator = AdminPanelValidator()

    class Meta:
        model = models.Profile
        fields = ('id', 'status', 'review_notes')

    def update(self, instance, validated_data):
        last_mile_profile = LMProfileStatusUpdater(self.admin_validator).update(instance, validated_data, self.context['request'].user)
        return last_mile_profile


class ImportFileSerializer(serializers.Serializer):
    file = serializers.FileField()


class BulkUpdateLastMileProfileStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=LastMileUserProfileUpdateAdminSerializer.Meta.model.ApprovalStatus.choices)
    user_ids = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), many=True, write_only=True)
    review_notes = serializers.CharField(required=False, allow_blank=True)

    admin_validator = AdminPanelValidator()

    def validate_status(self, value):
        self.admin_validator = AdminPanelValidator()
        self.admin_validator.validate_status(value)
        return value

    @transaction.atomic
    def update(self, validated_data, approver_user):
        validated_data = LMProfileStatusUpdater(self.admin_validator).bulk_update(validated_data, approver_user)
        return validated_data


class BulkReviewPointOfInterestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PointOfInterestSerializer.Meta.model.ApprovalStatus.choices)
    points_of_interest = serializers.PrimaryKeyRelatedField(queryset=models.PointOfInterest.objects.all(), many=True, write_only=True)
    review_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_status(self, value):
        self.admin_validator = AdminPanelValidator()
        self.admin_validator.validate_status(value)
        return value

    @transaction.atomic
    def update(self, validated_data, approver_user):
        points_of_interest = validated_data.pop('points_of_interest')
        status = validated_data.get('status')
        for poi in points_of_interest:
            if status == models.PointOfInterest.ApprovalStatus.REJECTED:
                poi.reject(approver_user, validated_data.get('review_notes'))
            elif status == models.PointOfInterest.ApprovalStatus.APPROVED:
                poi.approve(approver_user, validated_data.get('review_notes'))
        return validated_data


class LastMileUserProfileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='last_mile_profile.id', read_only=True)
    status = serializers.CharField(source='last_mile_profile.status', read_only=True)
    approved_by = MinimalUserSerializer(source='last_mile_profile.approved_by', read_only=True)
    approved_on = serializers.DateTimeField(source='last_mile_profile.approved_on', read_only=True)
    review_notes = serializers.CharField(source='last_mile_profile.review_notes', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'status', 'approved_by', 'approved_on', 'review_notes')


class LastMileProfileReportSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    ip_name = serializers.CharField(source='user.profile.organization.name', read_only=True)
    ip_number = serializers.CharField(source='user.profile.organization.vendor_number', read_only=True)
    created_by = MinimalUserSerializer(read_only=True)
    approved_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = models.Profile
        fields = ('id', 'first_name', 'last_name', 'email', 'ip_name', 'ip_number', 'created_by', 'approved_by', 'created_on', 'approved_on')


class UserImportSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[EmailValidator(), LowerCaseEmailValidator()])
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    ip_number = serializers.CharField()
    point_of_interests = serializers.SlugRelatedField(
        slug_field='p_code',
        many=True,
        queryset=models.PointOfInterest.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
        allow_empty=True
    )

    def validate_ip_number(self, value):
        try:
            return Organization.objects.get(vendor_number=value)
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Organization not found by vendor number")

    def create(self, validated_data, country_schema, created_by):
        validated_data['country_schema'] = country_schema
        validated_data['created_by'] = created_by
        validated_data['profile'] = {}
        validated_data['profile']['organization'] = validated_data.pop('ip_number')
        validated_data['profile']['job_title'] = ""
        validated_data['profile']['phone_number'] = ""
        validated_data['username'] = validated_data['email']
        try:
            user = LMUserCreator().create(validated_data)
        except Exception as ex:
            return False, str(ex)
        return True, user


class StockManagementImportSerializer(serializers.Serializer):
    ip_number = serializers.CharField()
    material_number = serializers.CharField()
    quantity = serializers.IntegerField()
    uom = serializers.CharField()
    expiration_date = serializers.DateTimeField(required=False, allow_null=True)
    batch_id = serializers.CharField(required=False, allow_null=True)
    p_code = serializers.CharField()

    adminValidator = AdminPanelValidator()

    def validate_ip_number(self, value):
        try:
            return PartnerOrganization.objects.get(organization__vendor_number=value)
        except PartnerOrganization.DoesNotExist:
            raise serializers.ValidationError("Partner Organization not found by vendor number")

    def validate_material_number(self, value):
        try:
            return models.Material.objects.get(number=value)
        except models.Material.DoesNotExist:
            raise serializers.ValidationError("Material not found by material number")

    def validate_quantity(self, value):
        self.adminValidator.validate_positive_quantity(value)
        return value

    def validate_uom(self, value):
        self.adminValidator.validate_uom(value)
        return value

    def validate_batch_id(self, value):
        if value:
            self.adminValidator.validate_batch_id(value)
        return value

    def validate_p_code(self, value):
        try:
            return models.PointOfInterest.objects.get(p_code=value)
        except models.PointOfInterest.DoesNotExist:
            raise serializers.ValidationError("Point of interest not found by p_code")

    def create(self, validated_data, created_by):
        validated_data['partner_organization'] = validated_data.pop('ip_number')
        validated_data['location'] = validated_data.pop('p_code')
        validated_data['created_by'] = created_by
        validated_data['items'] = [{
            'material': validated_data.pop('material_number'),
            'quantity': validated_data.pop('quantity'),
            'uom': validated_data.pop('uom'),
            'item_name': validated_data.pop('batch_id'),
            'expiration_date': validated_data.pop('expiration_date')
        }]
        instance = StockManagementCreateService().create_stock_management(validated_data)
        return True, instance


class LocationImportSerializer(serializers.Serializer):
    p_code_location = serializers.CharField()
    location_name = serializers.CharField()
    primary_type_name = serializers.CharField()
    latitude = serializers.CharField()
    longitude = serializers.CharField()
    ip_numbers = serializers.SlugRelatedField(
        slug_field='organization__vendor_number',
        many=True,
        queryset=PartnerOrganization.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
        allow_empty=True
    )

    def validate_p_code_location(self, value):
        try:
            data = models.PointOfInterest.objects.get(p_code=value)
            if data:
                raise serializers.ValidationError("Point of interest already exists")
        except models.PointOfInterest.DoesNotExist:
            return value

    def validate_location_name(self, value):
        try:
            data = models.PointOfInterest.objects.get(name=value)
            if data:
                raise serializers.ValidationError("Point of interest already exists")
            if not value:
                raise serializers.ValidationError("Point of interest name is required")
            if len(value) < 1:
                raise serializers.ValidationError("Point of interest name is required")
        except models.PointOfInterest.DoesNotExist:
            return value

    def validate_primary_type_name(self, value):
        poi_type = models.PointOfInterestType.objects.filter(name=value).first()
        if not poi_type:
            raise serializers.ValidationError("Point of interest type does not exist")
        return poi_type

    def validate_latitude(self, value):
        try:
            return float(value)
        except ValueError:
            raise serializers.ValidationError("Invalid latitude")

    def validate_longitude(self, value):
        try:
            return float(value)
        except ValueError:
            raise serializers.ValidationError("Invalid longitude")

    def create(self, validated_data, created_by):
        partner_organizations = validated_data.pop('ip_numbers')
        p_code_location = validated_data.pop('p_code_location')
        location_name = validated_data.pop('location_name')
        primary_type_name = validated_data.pop('primary_type_name')
        latitude = validated_data.pop('latitude')
        longitude = validated_data.pop('longitude')
        try:
            with transaction.atomic():
                point_of_interest = models.PointOfInterest.objects.create(
                    p_code=p_code_location,
                    name=location_name,
                    poi_type=primary_type_name,
                    point=Point(longitude, latitude),
                    created_by=created_by,
                    is_active=False,
                )
                point_of_interest.partner_organizations.set(partner_organizations)
        except Exception as ex:
            return False, str(ex)
        return True, point_of_interest


class MaterialsLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Material
        fields = ('id', 'number')


class ItemTransferRevertSerializer(serializers.ModelSerializer):
    material = MaterialsLightSerializer(read_only=True)
    uom = serializers.SerializerMethodField(read_only=True)

    def get_uom(self, obj):
        return obj.uom if obj.uom else obj.material.original_uom

    class Meta:
        model = models.Item
        fields = ('material', 'quantity', 'modified', 'batch_id', 'description', 'mapped_description', 'uom')


class TransferItemAdminSerializer(serializers.ModelSerializer):
    items = ItemTransferRevertSerializer(many=True, read_only=True)
    origin_point = serializers.CharField(source='origin_point.name', read_only=True)
    destination_point = serializers.CharField(source='destination_point.name', read_only=True)
    partner_organization = serializers.CharField(source='partner_organization.name', read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        reversed_origin_point, reversed_destination_point = ReverseTransfer(instance.pk).decide_origin_and_destination_location()
        data['reversed_origin_point'] = reversed_origin_point.name if reversed_origin_point else None
        data['reversed_destination_point'] = reversed_destination_point.name if reversed_destination_point else None
        return data

    class Meta:
        model = models.Transfer
        fields = ("id", "created", "modified", "unicef_release_order", "name", "transfer_type", "status", "partner_organization", "destination_point", "origin_point", "items")


class TransferReverseAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Transfer
        fields = ("id",)

    def update(self, instance, validated_data):
        reversed_transfer = ReverseTransfer(transfer_id=instance.pk).reverse()
        return reversed_transfer


class BulkReviewTransferSerializer(serializers.Serializer):
    approval_status = serializers.ChoiceField(choices=models.Transfer.ApprovalStatus.choices)
    items = serializers.PrimaryKeyRelatedField(queryset=models.Item.all_objects.select_related('transfer').all(), many=True, write_only=True)
    review_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    admin_validator = AdminPanelValidator()

    def validate_approval_status(self, value):
        self.admin_validator.validate_status(value)
        return value

    @transaction.atomic
    def update(self, validated_data, approver_user):
        items = validated_data.pop('items')
        approval_status = validated_data.get('approval_status')
        review_notes = validated_data.get('review_notes')
        TransferApprovalService().bulk_review(
            items=items,
            approval_status=approval_status,
            approver_user=approver_user,
            review_notes=review_notes
        )

        return validated_data
