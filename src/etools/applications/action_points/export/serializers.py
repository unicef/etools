from rest_framework import serializers


class ActionPointExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='reference_number')
    cp_output = serializers.CharField(source='cp_output.__str__')
    partner = serializers.CharField(source='partner.name')
    office = serializers.CharField(source='office.name')
    section = serializers.CharField(source='section.name')
    assigned_to = serializers.CharField(source='assigned_to.get_full_name')
    due_date = serializers.DateField(format='%d/%m/%Y')
    status = serializers.CharField(source='get_status_display')
    description = serializers.CharField()
    intervention = serializers.CharField(source='intervention.reference_number')
    pd_ssfa = serializers.CharField(source='intervention.title')
    location = serializers.CharField(source='location.__str__')
    related_module = serializers.CharField()
    assigned_by = serializers.CharField(source='assigned_by.get_full_name')
    date_of_completion = serializers.DateTimeField(format='%d/%m/%Y')
    related_ref = serializers.SerializerMethodField()
    related_object_url = serializers.SerializerMethodField()

    def get_related_ref(self, obj):
        return obj.related_object.reference_number if obj.related_object else None

    def get_related_object_url(self, obj):
        return obj.related_object.get_object_url() if obj.related_object else None
