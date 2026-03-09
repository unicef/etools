import types

from rest_framework import serializers
from unicef_attachments.models import Attachment, FileType
from unicef_attachments.serializers import AttachmentSerializerMixin


class AttachmentMultipleFileField(serializers.Field):

    def get_attribute(self, instance):
        if hasattr(instance, self.source):
            return getattr(instance, self.source)
        return None

    def to_representation(self, value):
        if not value:
            return []

        request = self.context.get('request', None)
        urls = []
        for attachment in value.all():
            if attachment.file:
                url = attachment.file.url
                if request is not None:
                    url = request.build_absolute_uri(url)
                urls.append(url)
            elif attachment.hyperlink:
                urls.append(attachment.hyperlink)
        return urls

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError("Expected a list of attachment IDs.")

        if not all(isinstance(pk, int) or (isinstance(pk, str) and pk.isdigit()) for pk in data):
            raise serializers.ValidationError("All items must be integer attachment IDs.")

        attachment_relation = getattr(self.parent.Meta.model, self.source)
        code = attachment_relation.field.code
        return data, code


def validate_multiple_attachments(cls, data):
    pk_list, code = data
    attachments = []

    for pk_value in pk_list:
        try:
            attachment = Attachment.objects.get(pk=int(pk_value))
        except (ValueError, TypeError):
            raise serializers.ValidationError(f"Attachment expects an integer, got {pk_value}")
        except Attachment.DoesNotExist:
            raise serializers.ValidationError(f"Attachment with pk={pk_value} does not exist")

        if attachment.content_object is not None:
            if not cls.instance or attachment.content_object != cls.instance:
                raise serializers.ValidationError(
                    "Attachment {} is already associated: {}".format(
                        pk_value, attachment.content_object
                    )
                )

        attachment.code = code
        try:
            attachment.file_type = FileType.objects.get(code=code)
        except (FileType.DoesNotExist, FileType.MultipleObjectsReturned):
            pass

        attachments.append(attachment)

    return attachments


class AttachmentMultipleSerializerMixin(AttachmentSerializerMixin):

    def __init__(self, *args, **kwargs):
        self.multiple_attachment_list = []
        super().__init__(*args, **kwargs)

    def check_attachment_fields(self):
        super().check_attachment_fields()

        for field_name, field in self.fields.items():
            if isinstance(field, AttachmentMultipleFileField):
                if not field.read_only and hasattr(self, "initial_data"):
                    if field_name in self.initial_data:
                        if self.initial_data[field_name] is None:
                            self.initial_data.pop(field_name)
                        else:
                            setattr(
                                self,
                                "validate_{}".format(field_name),
                                types.MethodType(validate_multiple_attachments, self),
                            )
                            self.multiple_attachment_list.append(field.source)
                    else:
                        setattr(field, "read_only", True)

    def save(self, *args, **kwargs):
        multiple_attachments_to_save = []
        for attachment_attr in self.multiple_attachment_list:
            attachment_list = self.validated_data.pop(attachment_attr, [])
            multiple_attachments_to_save.append(attachment_list)

        response = super().save(*args, **kwargs)

        for attachment_list in multiple_attachments_to_save:
            for attachment in attachment_list:
                if attachment.content_object is None:
                    attachment.content_object = self.instance
                attachment.save()

        return response
