from urllib.parse import urljoin

from rest_framework import serializers

from etools.applications.utils.common.urlresolvers import site_url


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
        return ', '.join(map(
            lambda a: '{} - {}'.format(a.file_type, urljoin(site_url(), a.url)),
            obj.attachments.all()
        ))
