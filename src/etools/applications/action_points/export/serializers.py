from rest_framework import serializers


class ActionPointExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='reference_number', read_only=True)
    cp_output = serializers.CharField(source='cp_output')
    partner = serializers.CharField(source='partner.name', default='')
    office = serializers.CharField(source='office.name', default='')
    section = serializers.CharField(source='section.name', default='')
    category = serializers.CharField(source='category.description', default='')
    assigned_to = serializers.CharField(source='assigned_to.get_full_name')
    due_date = serializers.DateField(format='%d/%m/%Y')
    status = serializers.CharField(source='get_status_display')
    description = serializers.CharField()
    intervention = serializers.CharField(source='intervention.reference_number', read_only=True, default='')
    pd_ssfa = serializers.CharField(source='intervention.title', default='')
    location = serializers.CharField(source='location')
    related_module = serializers.CharField()
    assigned_by = serializers.CharField(source='assigned_by.get_full_name')
    date_of_completion = serializers.DateTimeField(format='%d/%m/%Y')
    related_ref = serializers.CharField(source='related_object.reference_number', read_only=True, default='')
    related_object_str = serializers.CharField()
    related_object_url = serializers.CharField()
