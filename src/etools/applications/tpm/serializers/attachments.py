from django.utils.translation import gettext as _

from rest_framework import serializers
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import AttachmentLink, FileType
from unicef_attachments.serializers import AttachmentLinkSerializer, BaseAttachmentSerializer

from etools.applications.attachments.utils import get_file_type


class TPMPartnerAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        queryset=FileType.objects.group_by("tpm_partner"),
        label=_('Document Type'),
    )
    source = serializers.SerializerMethodField()

    class Meta(BaseAttachmentSerializer.Meta):
        fields = [
            'id',
            'file_type',
            'file',
            'hyperlink',
            'created',
            'modified',
            'uploaded_by',
            'filename',
            'source',
        ]

    def get_source(self, obj):
        return "Third Party Monitoring"


class ActivityAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        queryset=FileType.objects.group_by("tpm"),
        label=_('Document Type'),
    )

    class Meta(BaseAttachmentSerializer.Meta):
        fields = BaseAttachmentSerializer.Meta.fields + ['object_id']

    def create(self, validated_data):
        validated_data['code'] = 'activity_attachments'
        return super().create(validated_data)


class ActivityReportSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        queryset=FileType.objects.group_by("tpm_report"),
        label=_('Document Type'),
    )

    class Meta(BaseAttachmentSerializer.Meta):
        fields = BaseAttachmentSerializer.Meta.fields + ['object_id']

    def create(self, validated_data):
        validated_data['code'] = 'activity_report'
        return super().create(validated_data)


class TPMVisitReportAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        queryset=FileType.objects.group_by('tpm_report_attachments'),
        label=_('Document Type'),
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass

    def create(self, validated_data):
        validated_data['code'] = 'visit_report_attachments'
        return super().create(validated_data)


class TPMVisitAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        queryset=FileType.objects.group_by('tpm'),
        label=_('Document Type'),
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass

    def create(self, validated_data):
        validated_data['code'] = 'visit_attachments'
        return super().create(validated_data)


class TPMAttachmentLinkSerializer(AttachmentLinkSerializer):
    source = serializers.SerializerMethodField()
    activity_id = serializers.IntegerField(source="object_id", read_only=True)
    file_type = serializers.SerializerMethodField()

    class Meta(AttachmentLinkSerializer.Meta):
        fields = (
            "id",
            "attachment",
            "filename",
            "url",
            "file_type",
            "created",
            "source",
            "activity_id",
        )

    def get_source(self, obj):
        return "Third Party Monitoring"

    def get_file_type(self, obj):
        return get_file_type(obj.attachment)


class TPMActivityAttachmentLinkSerializer(serializers.Serializer):
    attachments = TPMAttachmentLinkSerializer(many=True, allow_empty=False)

    def create(self, validated_data):
        links = []
        for attachment in validated_data["attachments"]:
            links.append(AttachmentLink.objects.create(
                attachment=attachment["attachment"],
                content_type=self.context["content_type"],
                object_id=self.context["object_id"],
            ))
        return {"attachments": links}


class TPMVisitAttachmentLinkSerializer(serializers.Serializer):
    activity_attachments = TPMAttachmentLinkSerializer(
        many=True,
        read_only=True,
    )
