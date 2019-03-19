from rest_framework import serializers
from unicef_attachments.models import AttachmentLink
from unicef_attachments.serializers import AttachmentLinkSerializer

from etools.applications.attachments.utils import get_file_type, get_source


class ListAttachmentLinkSerializer(AttachmentLinkSerializer):
    source = serializers.SerializerMethodField()
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
        )

    def get_source(self, obj):
        return get_source(obj.attachment)

    def get_file_type(self, obj):
        return get_file_type(obj.attachment)


class BaseAttachmentLinkSerializer(serializers.Serializer):
    def create(self, validated_data):
        links = []
        for attachment in validated_data["attachments"]:
            links.append(AttachmentLink.objects.create(
                attachment=attachment["attachment"],
                content_type=self.context["content_type"],
                object_id=self.context["object_id"],
            ))
        return {"attachments": links}


class EngagementAttachmentLinkSerializer(BaseAttachmentLinkSerializer):
    attachments = ListAttachmentLinkSerializer(many=True, allow_empty=False)


class SpotCheckAttachmentLinkSerializer(BaseAttachmentLinkSerializer):
    attachments = ListAttachmentLinkSerializer(many=True, allow_empty=False)


class MicroAssessmentAttachmentLinkSerializer(BaseAttachmentLinkSerializer):
    attachments = ListAttachmentLinkSerializer(many=True, allow_empty=False)


class AuditAttachmentLinkSerializer(BaseAttachmentLinkSerializer):
    attachments = ListAttachmentLinkSerializer(many=True, allow_empty=False)


class SpecialAuditAttachmentLinkSerializer(BaseAttachmentLinkSerializer):
    attachments = ListAttachmentLinkSerializer(many=True, allow_empty=False)
