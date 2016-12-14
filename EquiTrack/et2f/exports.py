from __future__ import unicode_literals

from import_export import resources

from et2f.models import Travel

#TODO move this away from importexport to regular serializer and export like that.. talk with Zoli or Nik for examples

class TravelListExporter(resources.ModelResource):
    is_driver = resources.Field(attribute='get_is_driver')
    approval_date = resources.Field(attribute='get_approval_date')
    ta_reference_number = resources.Field(attribute='get_ta_reference_number')
    attachment_count = resources.Field(attribute='get_attachment_count')

    class Meta:
        model = Travel
        fields = ('id', 'reference_number', 'traveler', 'purpose', 'start_date', 'end_date', 'status', 'created',
                  'section', 'office', 'supervisor', 'ta_required', 'ta_reference_number', 'approval_date', 'is_driver',
                  'attachment_count')
        export_order = fields

    def get_is_driver(self, obj):
        return obj.is_driver

    def get_ta_reference_number(self, obj):
        return obj.ta_reference_number

    def get_approval_date(self, obj):
        return obj.approval_date

    def get_attachment_count(self, obj):
        return obj.attachment_count