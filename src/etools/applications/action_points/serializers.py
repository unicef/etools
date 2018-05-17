from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_comments.models import Comment
from rest_framework import serializers

from etools.applications.EquiTrack.utils import get_current_site
from etools.applications.action_points.models import ActionPoint
from etools.applications.EquiTrack.serializers import SnapshotModelSerializer
from etools.applications.locations.serializers import LocationLightSerializer
from etools.applications.partners.serializers.interventions_v2 import InterventionCreateUpdateSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.reports.serializers.v1 import ResultSerializer
from etools.applications.snapshot.serializers import ActivitySerializer
from etools.applications.users.models import Section
from etools.applications.users.serializers import OfficeSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer
from etools.applications.utils.common.serializers.fields import SeparatedReadWriteField
from etools.applications.utils.common.serializers.mixins import UserContextSerializerMixin
from etools.applications.utils.writable_serializers.serializers import WritableNestedSerializerMixin


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ('id', 'name')


class ActionPointBaseSerializer(UserContextSerializerMixin, SnapshotModelSerializer, serializers.ModelSerializer):
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
            'id', 'author', 'assigned_by', 'assigned_to',

            'high_priority', 'due_date', 'description',

            'created', 'date_of_completion',
            'status', 'status_date',
        ]
        extra_kwargs = {
            'status': {'read_only': True},
            'date_of_completion': {'read_only': True}
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


class ActionPointLightSerializer(PermissionsBasedSerializerMixin, ActionPointBaseSerializer):
    related_module = serializers.ReadOnlyField(label=_('Related Module'))
    reference_number = serializers.ReadOnlyField(label=_('Reference Number'))

    partner = SeparatedReadWriteField(
        read_field=MinimalPartnerOrganizationListSerializer(read_only=True, label=_('Partner')),
    )
    intervention = SeparatedReadWriteField(
        read_field=InterventionCreateUpdateSerializer(read_only=True, label=_('PD/SSFA')),
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
            'reference_number', 'related_module',

            'section', 'office', 'location',
            'partner', 'cp_output', 'intervention',
        ]


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


class ActionPointSerializer(WritableNestedSerializerMixin, ActionPointLightSerializer):
    comments = CommentSerializer(many=True, label=_('Comments'))
    history = ActivitySerializer(many=True, label=_('History'), read_only=True)

    related_object_str = serializers.SerializerMethodField(label=_('Reference'))
    related_object_url = serializers.SerializerMethodField()

    class Meta(WritableNestedSerializerMixin.Meta, ActionPointLightSerializer.Meta):
        fields = ActionPointLightSerializer.Meta.fields + [
            'comments', 'history', 'related_object_str', 'related_object_url',
        ]

    def get_related_object_str(self, obj):
        return str(obj.related_object) if obj.related_object else None

    def get_related_object_url(self, obj):
        return obj.related_object.get_object_url() if obj.related_object else None
