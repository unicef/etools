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
