from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from urllib.parse import urljoin

from etools.applications.field_monitoring.shared.models import FMMethod


class LocationSiteExportSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.max_admin_level = kwargs.pop('max_admin_level', 1)
        super().__init__(*args, **kwargs)

    id = serializers.CharField()
    parents_info = serializers.SerializerMethodField()
    site = serializers.CharField(source='name')
    lat = serializers.SerializerMethodField()
    long = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    security_detail = serializers.CharField()

    def get_parents_info(self, obj):
        parents = list(obj.parent.get_ancestors(include_self=True))
        parents = parents + [None] * (self.max_admin_level - len(parents))
        parents_info = {}

        for i, parent in enumerate(parents):
            level = i + 1
            parents_info.update({
                'admin_{}_name'.format(level): parent.name if parent else '',
                'admin_{}_type'.format(level): parent.gateway.name if parent else '',
                'admin_{}_pcode'.format(level): parent.p_code if parent else '',
            })

        return parents_info

    def get_lat(self, obj):
        if not obj.point:
            return ''

        return obj.point.coords[0]

    def get_long(self, obj):
        if not obj.point:
            return ''

        return obj.point.coords[1]

    def get_active(self, obj):
        return "Yes" if obj.is_active else "No"


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


class CheckListExportSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.methods = FMMethod.objects.all()
        super().__init__(*args, **kwargs)

    cp_output = serializers.CharField(source='cp_output_config.cp_output.name')
    category = serializers.CharField(source='checklist_item.category')
    checklist_item = serializers.CharField()
    by_partner = serializers.SerializerMethodField()
    specific_details = serializers.SerializerMethodField()
    selected_methods = serializers.SerializerMethodField()
    recommended_method_types = serializers.SerializerMethodField()

    def get_by_partner(self, obj):
        partners_info = obj.partners_info.all()
        if len(partners_info) == 0:
            return ''

        if any([i.partner for i in partners_info]):
            return _('by partner')
        return _('for all')

    def get_specific_details(self, obj):
        partners_info = obj.partners_info.all()
        if len(partners_info) == 0:
            return ''

        by_partner = any([i.partner for i in partners_info])
        if not by_partner:
            return partners_info[0].specific_details

        data = [
            '{info.partner.name}: {info.specific_details}'.format(info=info)
            for info in partners_info
        ]
        return ', '.join(data)

    def get_selected_methods(self, obj):
        return {
            m.name: '1' if m in obj.methods.all() else ''
            for m in self.methods
        }

    def get_recommended_method_types(self, obj):
        return {
            m.name: ', '.join([
                mt.name
                for mt in obj.cp_output_config.recommended_method_types.all()
                if mt.method == m
            ])
            for m in self.methods
            if m.is_types_applicable
        }
