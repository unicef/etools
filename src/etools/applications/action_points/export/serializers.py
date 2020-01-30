from rest_framework import serializers

from etools.applications.core.urlresolvers import build_frontend_url


class ActionPointExportSerializer(serializers.Serializer):

    ref = serializers.CharField(source='reference_number', read_only=True)
    ref_link = serializers.SerializerMethodField()
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
    related_ref = serializers.SerializerMethodField()
    related_object_url = serializers.SerializerMethodField()
    related_object_str = serializers.SerializerMethodField()
    action_taken = serializers.SerializerMethodField()

    def get_action_taken(self, obj):
        return ";\n\n".join(["{} ({}): {}".format(c.user if c.user else '-', c.submit_date.strftime(
            "%d %b %Y"), c.comment) for c in obj.comments.all()])

    def get_ref_link(self, obj):
        return obj.get_object_url()

    def get_related_ref(self, obj):
        if obj.travel_activity:
            return obj.travel_activity.primary_ref_number
        if obj.related_object:
            return obj.related_object.reference_number
        return None

    def get_related_object_str(self, obj):
        if obj.travel_activity:
            return f'Task No {obj.travel_activity.task_number} for Visit {obj.travel_activity.travel_id}'
        return obj.related_object_str

    def get_related_object_url(self, obj):
        if obj.travel_activity:
            return build_frontend_url('t2f', 'edit-travel', obj.travel_activity.travel_id)
        return obj.related_object_url
