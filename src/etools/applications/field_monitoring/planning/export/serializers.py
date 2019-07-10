from urllib.parse import urljoin

from django.conf import settings

from rest_framework import serializers


class LogIssueExportSerializer(serializers.Serializer):
    related_to = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    issue = serializers.CharField()
    status = serializers.CharField(source='get_status_display')
    attachments = serializers.SerializerMethodField()

    def get_related_to(self, obj):
        return dict(obj.RELATED_TO_TYPE_CHOICES).get(obj.related_to_type, '')

    def get_name(self, obj):
        return str(obj.related_to.name) if obj.related_to else ''

    def get_attachments(self, obj):
        return ', '.join([
            '{} - {}'.format(a.file_type, urljoin(settings.HOST, a.url))
            for a in obj.attachments.all()
        ])
