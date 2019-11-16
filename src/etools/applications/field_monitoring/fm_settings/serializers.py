import json

from django.contrib.gis.db.models import Collect
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import AttachmentLinkSerializer, BaseAttachmentSerializer
from unicef_locations.serializers import LocationLightSerializer, LocationSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin, WritableNestedSerializerMixin
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import HistorySerializer
from etools.applications.field_monitoring.fm_settings.models import (
    Category,
    LocationSite,
    LogIssue,
    Method,
    Option,
    Question,
)
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v2 import OutputListSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer


class MethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Method
        fields = ('id', 'name')


class FieldMonitoringGeneralAttachmentSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='fm_common')
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass


class ResultSerializer(OutputListSerializer):
    name = serializers.ReadOnlyField()

    class Meta(OutputListSerializer.Meta):
        pass


class OptionSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = Option
        fields = ('id', 'label', 'value')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class QuestionLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = (
            'id', 'answer_type', 'choices_size', 'level',
            'methods', 'category', 'sections', 'text',
            'is_hact', 'is_active', 'is_custom'
        )


class QuestionSerializer(WritableNestedSerializerMixin, QuestionLightSerializer):
    options = OptionSerializer(many=True, required=False)

    class Meta(WritableNestedSerializerMixin.Meta, QuestionLightSerializer.Meta):
        fields = QuestionLightSerializer.Meta.fields + ('options',)
        read_only_fields = ('is_custom',)

    def create(self, validated_data):
        validated_data['is_custom'] = True
        return super().create(validated_data)


class LocationSiteLightSerializer(serializers.ModelSerializer):
    parent = LocationSerializer(read_only=True)
    is_active = serializers.ChoiceField(choices=(
        (True, _('Active')),
        (False, _('Inactive')),
    ), label=_('Status'), required=False)

    class Meta:
        model = LocationSite
        fields = ['id', 'name', 'p_code', 'parent', 'point', 'is_active']
        extra_kwargs = {
            'point': {'required': True},
        }


class LocationSiteSerializer(LocationSiteLightSerializer):
    parent = LocationSerializer(read_only=True)

    class Meta(LocationSiteLightSerializer.Meta):
        pass


class LocationFullSerializer(LocationLightSerializer):
    point = serializers.SerializerMethodField()
    geom = serializers.SerializerMethodField()
    is_leaf = serializers.BooleanField(source='is_leaf_node', read_only=True)

    class Meta(LocationLightSerializer.Meta):
        fields = LocationLightSerializer.Meta.fields + ('point', 'geom', 'is_leaf')

    def get_geom(self, obj):
        return json.loads(obj.geom.json) if obj.geom else {}

    def get_point(self, obj):
        point = obj.point or self.Meta.model.objects.aggregate(boundary=Collect('point'))['boundary'].centroid
        return json.loads(point.json)


class LogIssueAttachmentSerializer(BaseAttachmentSerializer):
    class Meta(BaseAttachmentSerializer.Meta):
        pass


class LogIssueSerializer(UserContextSerializerMixin, SnapshotModelSerializer):
    author = MinimalUserSerializer(read_only=True, label=LogIssue._meta.get_field('author').verbose_name)
    closed_by = serializers.SerializerMethodField(label=_('Issue Closed By'))
    related_to_type = serializers.ChoiceField(choices=LogIssue.RELATED_TO_TYPE_CHOICES, read_only=True,
                                              label=_('Issue Related To'))

    cp_output = SeparatedReadWriteField(read_field=OutputListSerializer())
    partner = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer())
    location = SeparatedReadWriteField(read_field=LocationLightSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteLightSerializer())

    attachments = LogIssueAttachmentSerializer(many=True, read_only=True)
    history = HistorySerializer(many=True, read_only=True)

    class Meta:
        model = LogIssue
        fields = (
            'id', 'related_to_type', 'author',
            'cp_output', 'partner', 'location', 'location_site',
            'issue', 'status', 'attachments', 'history', 'closed_by',
        )

    def create(self, validated_data):
        validated_data['author'] = self.get_user()
        return super().create(validated_data)

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        provided_values = [v for v in [
            validated_data.get('cp_output', self.instance.cp_output if self.instance else None),
            validated_data.get('partner', self.instance.partner if self.instance else None),
            validated_data.get('location', self.instance.location if self.instance else None),
        ] if v]

        if not provided_values:
            raise ValidationError(_('Related object not provided'))

        if len(provided_values) != 1:
            raise ValidationError(_('Maximum one related object should be provided'))

        return validated_data

    def get_closed_by(self, obj):
        matched_events = [
            history for history in obj.history.all()
            if history.change.get('status', {}).get('after') == LogIssue.STATUS_CHOICES.past
        ]
        if not matched_events:
            return

        return MinimalUserSerializer(matched_events[-1].by_user).data


class FMCommonAttachmentLinkSerializer(BulkSerializerMixin, AttachmentLinkSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='fm_common'),
                                         write_only=True, required=True)

    class Meta(AttachmentLinkSerializer.Meta):
        list_serializer_class = BulkListSerializer
        update_lookup_field = 'attachment'

    def _set_file_type(self, instance, file_type=None):
        if file_type:
            instance.attachment.file_type = file_type
            instance.attachment.save()

    def create(self, validated_data):
        file_type = validated_data.pop('file_type', None)

        instance = super().create(validated_data)
        self._set_file_type(instance, file_type)

        return instance

    def update(self, instance, validated_data):
        validated_data = validated_data or {}
        file_type = validated_data.pop('file_type', None)

        instance = super().update(instance, validated_data)
        self._set_file_type(instance, file_type)

        return instance
