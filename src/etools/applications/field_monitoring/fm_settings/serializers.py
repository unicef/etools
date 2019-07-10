from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer

from etools.applications.field_monitoring.fm_settings.models import Method
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin
from etools.applications.reports.serializers.v2 import OutputListSerializer


class MethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Method
        fields = ('id', 'name')


class FieldMonitoringGeneralAttachmentSerializer(SafeReadOnlySerializerMixin, BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='fm_common')
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass


class ResultSerializer(OutputListSerializer):
    name = serializers.ReadOnlyField()

    class Meta(OutputListSerializer.Meta):
        pass
