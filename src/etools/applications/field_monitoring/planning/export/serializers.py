from rest_framework import serializers


class TaskExportSerializer(serializers.Serializer):
    id = serializers.CharField()
    cp_output = serializers.CharField(source='cp_output_config.cp_output.name')
    priority = serializers.SerializerMethodField()
    partner = serializers.StringRelatedField()
    pd_ssfa = serializers.StringRelatedField()
    location = serializers.StringRelatedField()
    location_site_id = serializers.CharField()
    location_site = serializers.StringRelatedField()
    plan_by_month = serializers.SerializerMethodField()

    def get_priority(self, obj):
        return 'Yes' if obj.cp_output_config.is_priority else 'No'

    def get_plan_by_month(self, obj):
        if not obj.plan_by_month or len(obj.plan_by_month) != 12:
            return [''] * 12

        return [(str(p) if p else '') for p in obj.plan_by_month]
