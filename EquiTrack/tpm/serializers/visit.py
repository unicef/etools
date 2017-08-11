from rest_framework import serializers

from locations.serializers import LocationLightSerializer
from partners.models import InterventionResultLink
from partners.serializers.interventions_v2 import InterventionCreateUpdateSerializer
from reports.serializers.v1 import SectorLightSerializer
from tpm.models import TPMVisit, TPMLocation, TPMPermission, TPMActivity, TPMSectorCovered, TPMLowResult
from tpm.serializers.attachments import TPMAttachmentsSerializer, TPMReportAttachmentsSerializer
from utils.permissions.serializers import StatusPermissionsBasedSerializerMixin, \
    StatusPermissionsBasedRootSerializerMixin
from utils.common.serializers.fields import SeparatedReadWriteField
from tpm.serializers.partner import TPMPartnerLightSerializer
from users.serializers import MinimalUserSerializer
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class TPMPermissionsBasedSerializerMixin(StatusPermissionsBasedSerializerMixin):
    class Meta(StatusPermissionsBasedSerializerMixin.Meta):
        permission_class = TPMPermission


class InterventionResultLinkVisitSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="cp_output.name")

    class Meta:
        model = InterventionResultLink
        fields = [
            'id', 'name'
        ]


class TPMLocationSerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                            serializers.ModelSerializer):
    location = SeparatedReadWriteField(
        read_field=LocationLightSerializer(read_only=True),
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMLocation
        fields = ['id', 'location', 'start_date', 'end_date', 'type_of_site']

    def validate(self, data):
        validated_data = super(TPMLocationSerializer, self).validate(data)
        return validated_data


class TPMLowResultSerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                             serializers.ModelSerializer):
    tpm_locations = TPMLocationSerializer(many=True)
    result = SeparatedReadWriteField(
        read_field=InterventionResultLinkVisitSerializer(read_only=True)
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMLowResult
        fields = ['id', 'result', 'tpm_locations']


class TPMSectorCoveredSerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                                 serializers.ModelSerializer):
    tpm_low_results = TPMLowResultSerializer(many=True)
    sector = SeparatedReadWriteField(
        read_field=SectorLightSerializer(read_only=True),
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMSectorCovered
        fields = ['id', 'sector', 'tpm_low_results']


class TPMActivitySerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                            serializers.ModelSerializer):
    tpm_sectors = TPMSectorCoveredSerializer(many=True)

    partnership = SeparatedReadWriteField(
        read_field=InterventionCreateUpdateSerializer(read_only=True),
    )

    unicef_focal_points = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True, many=True),
        required=False
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMActivity
        fields = ['id', 'partnership', 'tpm_sectors', 'unicef_focal_points']

    def _validate_sectors(self, tpm_sectors, partnership):
        if tpm_sectors:
            sector_ids = filter(lambda x: x, map(lambda s: s["sector"].id if "sector" in s else None, tpm_sectors))
            allowed = partnership.sector_locations.values_list('sector_id', flat=True)
            if len(set(sector_ids) - set(allowed)) > 0:
                raise serializers.ValidationError({
                    'tpm_sectors': ' '.join([
                        ','.join(map(str, set(sector_ids) - set(allowed))),
                        'is not allowed for',
                        str(partnership)
                    ])
                })

    def _validate_tpm_low_results(self, sector, partnership):
        result_errors = []
        for result in sector.get("tpm_low_results", []):
            result_error = None

            tpm_locations = result.get("tpm_locations", [])

            if result.get("result", None) and not partnership.result_links.filter(id=result.get("result").id).exists():
                result_error = '{} not allowed for {}'.format(result.get("result"), partnership)

            location_errors = []
            for tpm_location in tpm_locations:

                location = tpm_location.get('location', None)
                if location:
                    if not partnership.sector_locations.filter(
                        sector=sector["sector"], locations=location
                    ).exists():
                        location_errors.append('{0} not allowed for {1}'.format(location, sector["sector"]))

            errors = {}
            if location_errors:
                errors["tpm_locations"] = location_errors
            if result_error:
                errors["result"] = result_error
            if errors:
                result_errors.append(errors)

        if result_errors:
            raise serializers.ValidationError({
                "tpm_low_results": result_errors
            })

    def validate(self, data):
        validated_data = super(TPMActivitySerializer, self).validate(data)

        instance = self.root.instance.tpm_activities.get(id=validated_data['id']) if 'id' in validated_data else None
        partnership = instance.partnership if instance else validated_data['partnership']
        tpm_sectors = validated_data.get('tpm_sectors', [])

        self._validate_sectors(tpm_sectors, partnership)
        for sector in tpm_sectors:
            self._validate_tpm_low_results(sector, partnership)

        return validated_data


class TPMVisitLightSerializer(StatusPermissionsBasedRootSerializerMixin, WritableNestedSerializerMixin,
                              serializers.ModelSerializer):
    tpm_activities = TPMActivitySerializer(many=True, required=False)

    tpm_partner = SeparatedReadWriteField(
        read_field=TPMPartnerLightSerializer(read_only=True),
    )

    status_date = serializers.ReadOnlyField()

    class Meta(StatusPermissionsBasedRootSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMVisit
        permission_class = TPMPermission
        fields = [
            'id', 'start_date', 'end_date',
            'tpm_activities', 'tpm_partner',
            'status', 'status_date', 'reference_number',
        ]


class TPMVisitSerializer(TPMVisitLightSerializer):
    attachments = TPMAttachmentsSerializer(many=True, required=False)
    report = TPMReportAttachmentsSerializer(many=True, required=False)

    class Meta(TPMVisitLightSerializer.Meta):
        fields = TPMVisitLightSerializer.Meta.fields + [
            'reject_comment',
            'attachments',
            'report',
        ]
        extra_kwargs = {
            'tpm_partner': {'required': True},
        }


class TPMVisitDraftSerializer(TPMVisitSerializer):
    class Meta(TPMVisitSerializer.Meta):
        extra_kwargs = {
            'tpm_partner': {'required': False},
        }
