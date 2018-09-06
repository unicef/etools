from rest_framework import serializers


class ActionPointExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='reference_number', read_only=True)
    cp_output = serializers.SerializerMethodField()
    partner = serializers.SerializerMethodField()
    office = serializers.SerializerMethodField()
    section = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    assigned_to = serializers.CharField(source='assigned_to.get_full_name')
    due_date = serializers.DateField(format='%d/%m/%Y')
    status = serializers.CharField(source='get_status_display')
    description = serializers.CharField()
    intervention = serializers.CharField(source='intervention.reference_number', read_only=True)
    pd_ssfa = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    related_module = serializers.CharField()
    assigned_by = serializers.CharField(source='assigned_by.get_full_name')
    date_of_completion = serializers.DateTimeField(format='%d/%m/%Y')
    related_ref = serializers.CharField(source='related_object.reference_number', read_only=True)
    related_object_str = serializers.CharField()
    related_object_url = serializers.CharField()

    def get_cp_output(self, obj):
        return obj.cp_output.__str__ if obj.cp_output else ""

    def get_partner(self, obj):
        return obj.partner.name if obj.partner else ""

    def get_office(self, obj):
        return obj.office.name if obj.office else ""

    def get_section(self, obj):
        return obj.section.name if obj.section else ""

    def get_category(self, obj):
        return obj.category.description if obj.category else ""

    def get_pd_ssfa(self, obj):
        return obj.intervention.title if obj.intervention else ""

    def get_location(self, obj):
        return obj.location.__str__ if obj.location else ""
