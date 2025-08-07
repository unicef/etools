from urllib.parse import urljoin

from django.conf import settings
from django.utils.translation import gettext as _

from rest_framework import serializers


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

    def get_parents_info(self, obj):
        parents = list(obj.parent.get_ancestors(include_self=True))
        parents = parents + [None] * (self.max_admin_level - len(parents))
        parents_info = {}

        for i, parent in enumerate(parents):
            level = i + 1
            parents_info.update({
                'admin_{}_name'.format(level): parent.name if parent else '',
                'admin_{}_type'.format(level): parent.admin_level_name if parent else '',
                'admin_{}_pcode'.format(level): parent.p_code if parent else '',
            })

        return parents_info

    def get_lat(self, obj):
        if not obj.point:
            return ''

        return obj.point.coords[1]

    def get_long(self, obj):
        if not obj.point:
            return ''

        return obj.point.coords[0]

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


class QuestionExportSerializer(serializers.Serializer):
    category = serializers.SerializerMethodField()
    text = serializers.CharField()
    level = serializers.SerializerMethodField()
    answer_type = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_hact = serializers.SerializerMethodField()
    is_custom = serializers.SerializerMethodField()
    methods = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()

    def get_category(self, obj):
        return obj.category.name if obj.category else ''

    def get_level(self, obj):
        return dict(obj.LEVELS).get(obj.level, obj.level)

    def get_answer_type(self, obj):
        return dict(obj.ANSWER_TYPES).get(obj.answer_type, obj.answer_type)

    def get_methods(self, obj):
        return ', '.join([m.name for m in obj.methods.all()])

    def get_sections(self, obj):
        return ', '.join([s.name for s in obj.sections.all()])

    def get_options(self, obj):
        return ', '.join([opt.label for opt in obj.options.all()])

    def get_is_active(self, obj):
        return _("Yes") if obj.is_active else _("No")

    def get_is_hact(self, obj):
        return _("Yes") if obj.is_hact else _("No")

    def get_is_custom(self, obj):
        return _("Yes") if obj.is_custom else _("No")
