from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import HistorySerializer
from etools.applications.field_monitoring.fm_settings.models import LogIssue
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin
from etools.applications.reports.serializers.v2 import OutputListSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer


class LogIssueAttachmentSerializer(SafeReadOnlySerializerMixin, BaseAttachmentSerializer):
    class Meta(BaseAttachmentSerializer.Meta):
        pass


class LogIssueSerializer(UserContextSerializerMixin, SafeReadOnlySerializerMixin, SnapshotModelSerializer):
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
