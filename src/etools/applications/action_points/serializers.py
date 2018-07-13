from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_comments.models import Comment
from rest_framework import serializers
from unicef_snapshot.models import Activity
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.EquiTrack.utils import get_current_site
from etools.applications.action_points.models import ActionPoint
from etools.applications.locations.serializers import LocationLightSerializer
from etools.applications.partners.serializers.interventions_v2 import BaseInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.reports.serializers.v1 import ResultSerializer, SectionSerializer
from etools.applications.users.serializers import OfficeSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer
from etools.applications.utils.common.serializers.fields import SeparatedReadWriteField
from etools.applications.utils.common.serializers.mixins import UserContextSerializerMixin
from etools.applications.utils.writable_serializers.serializers import WritableNestedSerializerMixin


class ActionPointBaseSerializer(UserContextSerializerMixin, SnapshotModelSerializer, serializers.ModelSerializer):
    reference_number = serializers.ReadOnlyField(label=_('Reference Number'))
    author = MinimalUserSerializer(read_only=True, label=_('Author'))
    assigned_by = MinimalUserSerializer(read_only=True, label=_('Assigned By'))
    assigned_to = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True, label=_('Assigned To')),
        required=True
    )

    status_date = serializers.DateTimeField(read_only=True, label=_('Status Date'))

    class Meta:
        model = ActionPoint
        fields = [
            'id', 'reference_number',
            'author', 'assigned_by', 'assigned_to',

            'high_priority', 'due_date', 'description',

            'created', 'date_of_completion',
            'status', 'status_date',
        ]
        extra_kwargs = {
            'status': {'read_only': True},
            'date_of_completion': {'read_only': True},
            'due_date': {'required': True},
        }

    def create(self, validated_data):
        validated_data.update({
            'author': self.get_user(),
            'assigned_by': self.get_user()
        })

        return super(ActionPointBaseSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        if 'assigned_to' in validated_data:
            validated_data['assigned_by'] = self.get_user()

        return super(ActionPointBaseSerializer, self).update(instance, validated_data)


class ActionPointListSerializer(PermissionsBasedSerializerMixin, ActionPointBaseSerializer):
    related_module = serializers.ChoiceField(label=_('Related Module'), choices=ActionPoint.MODULE_CHOICES,
                                             read_only=True)

    partner = SeparatedReadWriteField(
        read_field=MinimalPartnerOrganizationListSerializer(read_only=True, label=_('Partner')),
    )
    intervention = SeparatedReadWriteField(
        read_field=BaseInterventionListSerializer(read_only=True, label=_('PD/SSFA')),
        required=False,
    )

    cp_output = SeparatedReadWriteField(
        read_field=ResultSerializer(read_only=True, label=_('CP Output')),
        required=False,
    )

    location = SeparatedReadWriteField(
        read_field=LocationLightSerializer(read_only=True, label=_('Location')),
    )

    section = SeparatedReadWriteField(
        read_field=SectionSerializer(read_only=True, label=_('Section')),
        required=True,
    )
    office = SeparatedReadWriteField(
        read_field=OfficeSerializer(read_only=True, label=_('Office')),
        required=True
    )

    class Meta(ActionPointBaseSerializer.Meta):
        fields = ActionPointBaseSerializer.Meta.fields + [
            'related_module',

            'section', 'office', 'location',
            'partner', 'cp_output', 'intervention',

            'engagement', 'tpm_activity', 'travel',
        ]

    def create(self, validated_data):
        if 'engagement' in validated_data:
            engagement = validated_data['engagement']
            validated_data.update({
                'partner_id': engagement.partner_id,
            })
        elif 'tpm_activity' in validated_data:
            activity = validated_data['tpm_activity']
            validated_data.update({
                'partner_id': activity.partner_id,
                'intervention_id': activity.intervention_id,
                'cp_output_id': activity.cp_output_id,
                'section_id': activity.section_id,
            })
        elif 'travel' in validated_data:
            travel = validated_data['travel']
            validated_data.update({
                'office_id': travel.office_id,
                'section_id': travel.section_id,
            })

        return super().create(validated_data)


class CommentSerializer(UserContextSerializerMixin, WritableNestedSerializerMixin, serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True, label=_('Author'))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = Comment
        fields = (
            'id', 'user', 'comment', 'submit_date'
        )
        extra_kwargs = {
            'user': {'read_only': True},
            'submit_date': {'read_only': True},
        }

    def create(self, validated_data):
        validated_data.update({
            'user': self.get_user(),
            'submit_date': timezone.now(),
            'site': get_current_site(),
        })
        return super(CommentSerializer, self).create(validated_data)


class HistorySerializer(serializers.ModelSerializer):
    by_user_display = serializers.ReadOnlyField(source='by_user.get_full_name', label=_('User'))
    action = serializers.SerializerMethodField(label=_('Action'))

    class Meta:
        model = Activity
        fields = ('id', 'created', 'by_user_display', 'action')
        extra_kwargs = {
            'created': {'label': _('Date')},
        }

    def get_action(self, obj):
        return ActionPoint.get_snapshot_action_display(obj)


class ActionPointSerializer(WritableNestedSerializerMixin, ActionPointListSerializer):
    comments = CommentSerializer(many=True, label=_('Actions Taken'))
    history = HistorySerializer(many=True, label=_('History'), read_only=True, source='get_meaningful_history')

    related_object_str = serializers.SerializerMethodField(label=_('Reference'))
    related_object_url = serializers.SerializerMethodField()

    class Meta(WritableNestedSerializerMixin.Meta, ActionPointListSerializer.Meta):
        fields = ActionPointListSerializer.Meta.fields + [
            'comments', 'history', 'related_object_str', 'related_object_url',
        ]

    def get_related_object_str(self, obj):
        return str(obj.related_object) if obj.related_object else None

    def get_related_object_url(self, obj):
        return obj.related_object.get_object_url() if obj.related_object else None
