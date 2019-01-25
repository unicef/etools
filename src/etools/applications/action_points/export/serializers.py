from rest_framework import serializers
from unicef_restlib.fields import FunctionRelatedField


def comment_export_function(obj):
    user = obj.user if obj.user else '-'
    return f'{user} ({obj.submit_date.strftime("%d %b %Y")}) {obj.comment}'


class ActionPointExportSerializer(serializers.Serializer):

    ref = serializers.CharField(source='reference_number', read_only=True)
    cp_output = serializers.CharField(allow_null=True)
    partner = serializers.CharField(source='partner.name', allow_null=True)
    office = serializers.CharField(source='office.name', allow_null=True)
    section = serializers.CharField(source='section.name', allow_null=True)
    category = serializers.CharField(source='category.description', allow_null=True)
    assigned_to = serializers.CharField(source='assigned_to.get_full_name', allow_null=True)
    due_date = serializers.DateField(format='%d/%m/%Y')
    status = serializers.CharField(source='get_status_display')
    description = serializers.CharField()
    high_priority = serializers.BooleanField()
    intervention = serializers.CharField(source='intervention.reference_number', read_only=True, allow_null=True)
    pd_ssfa = serializers.CharField(source='intervention.title', allow_null=True)
    location = serializers.CharField(allow_null=True)
    related_module = serializers.CharField()
    assigned_by = serializers.CharField(source='assigned_by.get_full_name', allow_null=True)
    date_of_completion = serializers.DateTimeField(format='%d/%m/%Y')
    related_ref = serializers.CharField(source='related_object.reference_number', read_only=True, allow_null=True)
    related_object_str = serializers.CharField()
    related_object_url = serializers.CharField()
    action_taken = FunctionRelatedField(source='comments', many=True, read_only=True,
                                        callable_function=comment_export_function)
