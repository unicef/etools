import json
from copy import copy

from django.contrib.gis.db.models import Collect
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationLightSerializer, LocationSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin
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
        fields = ('id', 'name', 'short_name', 'use_information_source')


class ResultSerializer(OutputListSerializer):
    name = serializers.ReadOnlyField()

    class Meta(OutputListSerializer.Meta):
        pass


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ('label', 'value')
        extra_kwargs = {
            'label': {'required': True},
            'value': {'required': True},
        }


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


class QuestionSerializer(QuestionLightSerializer):
    options = OptionSerializer(many=True, required=False)

    class Meta(QuestionLightSerializer.Meta):
        fields = QuestionLightSerializer.Meta.fields + ('options',)
        read_only_fields = ('is_custom',)

    def create(self, validated_data):
        validated_data['is_custom'] = True
        options = validated_data.pop('options', None)
        instance = super().create(validated_data)
        self.set_options(instance, options)
        return instance

    def update(self, instance, validated_data):
        options = validated_data.pop('options', None)
        instance = super().update(instance, validated_data)
        self.set_options(instance, options)
        return instance

    def set_options(self, instance, options):
        if options is None:
            return

        updated_pks = []
        for option in options:
            updated_pks.append(
                Option.objects.update_or_create(
                    question=instance, value=option['value'],
                    defaults={'label': option['label']}
                )[0].id
            )

        # cleanup, remove unused options
        instance.options.exclude(pk__in=updated_pks).delete()


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
        if not obj.geom:
            return {}

        # simplify geometry to avoid huge polygons
        return json.loads(obj.geom.simplify(0.003).json)

    def get_point(self, obj):
        point = obj.point

        if not point and obj.geom:
            # get center point from geometry
            point = obj.geom.centroid

        if not point:
            # get center point from nested locations boundary
            boundary = self.Meta.model.objects.filter(parent=obj).aggregate(boundary=Collect('point'))['boundary']
            if boundary:
                point = boundary.centroid

        return json.loads(point.json) if point else {}


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

        try:
            LogIssue._validate_related_objects(
                validated_data.get('cp_output', self.instance.cp_output if self.instance else None),
                validated_data.get('partner', self.instance.partner if self.instance else None),
                validated_data.get('location', self.instance.location if self.instance else None),
            )
        except DjangoValidationError as ex:
            raise ValidationError(ex.messages)

        return validated_data

    def get_closed_by(self, obj):
        matched_events = [
            history for history in obj.history.all()
            if history.change.get('status', {}).get('after') == LogIssue.STATUS_CHOICES.past
        ]
        if not matched_events:
            return

        return MinimalUserSerializer(matched_events[-1].by_user).data


class LinkedAttachmentBaseSerializer(BaseAttachmentSerializer):
    class Meta(BaseAttachmentSerializer.Meta):
        extra_kwargs = copy(BaseAttachmentSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'id': {'read_only': False},
            'file': {'read_only': True},
            'hyperlink': {'read_only': True},
        })

    def _validate_attachment(self, validated_data, instance=None):
        """file shouldn't be editable"""
        return


class FMCommonAttachmentSerializer(LinkedAttachmentBaseSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='fm_common'), required=True)

    class Meta(LinkedAttachmentBaseSerializer.Meta):
        pass
