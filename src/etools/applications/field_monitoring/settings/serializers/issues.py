from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import HistorySerializer
from etools.applications.field_monitoring.settings.models import LogIssue
from etools.applications.field_monitoring.settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v2 import OutputListSerializer


class LogIssueAttachmentSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code=LogIssue.ATTACHMENTS_FILE_TYPE_CODE)
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass


class LogIssueLightSerializer(serializers.ModelSerializer):
    related_to_type = serializers.ChoiceField(choices=LogIssue.RELATED_TO_TYPE_CHOICES, read_only=True,
                                              label=_('Issue Related To'))

    cp_output = SeparatedReadWriteField(read_field=OutputListSerializer())
    partner = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer())
    location = SeparatedReadWriteField(read_field=LocationLightSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteLightSerializer())

    attachments = LogIssueAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = LogIssue
        fields = (
            'id', 'related_to_type',
            'cp_output', 'partner', 'location', 'location_site',
            'issue', 'status', 'attachments',
        )


class LogIssueSerializer(SnapshotModelSerializer, LogIssueLightSerializer):
    history = HistorySerializer(many=True, read_only=True)

    class Meta(LogIssueLightSerializer.Meta):
        fields = LogIssueLightSerializer.Meta.fields + ('history',)

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        try:
            self.Meta.model.clean_related_to(
                validated_data.get('cp_output', self.instance.cp_output if self.instance else None),
                validated_data.get('partner', self.instance.partner if self.instance else None),
                validated_data.get('location', self.instance.location if self.instance else None),
                validated_data.get('location_site', self.instance.location_site if self.instance else None),
            )
        except DjangoValidationError as ex:
            raise ValidationError(ex.message)

        return validated_data
