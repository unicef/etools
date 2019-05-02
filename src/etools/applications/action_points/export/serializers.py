from django.urls import reverse
from rest_framework import serializers


class ActionPointExportSerializer(serializers.Serializer):

    ref = serializers.SerializerMethodField()
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
    action_taken = serializers.SerializerMethodField()

    def get_action_taken(self, obj):
        return ";\n\n".join(["{} ({}): {}".format(c.user if c.user else '-', c.submit_date.strftime(
            "%d %b %Y"), c.comment) for c in obj.comments.all()])

    def get_ref(self, obj):
        return "https://{}{}".format(
            self.context['request'].get_host(),
            reverse("action-points:action-points-detail", args=[obj.pk]),
        )
