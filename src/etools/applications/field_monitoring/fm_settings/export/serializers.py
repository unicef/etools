from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from etools.applications.field_monitoring.shared.models import FMMethod


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

        if any(map(lambda i: i.partner, partners_info)):
            return _('by partner')
        return _('for all')

    def get_specific_details(self, obj):
        partners_info = obj.partners_info.all()
        if len(partners_info) == 0:
            return ''

        by_partner = any(map(lambda i: i.partner, partners_info))
        if not by_partner:
            return partners_info[0].specific_details

        data = [
            '{info.partner.name}: {info.specific_details}'.format(info=info)
            for info in obj.partners_info.all()
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
