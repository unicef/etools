from __future__ import unicode_literals

from import_export import resources

from et2f.models import Travel


class TravelListExporter(resources.ModelResource):
    class Meta:
        model = Travel
        fields = ('id', 'reference_number', 'traveller', 'purpose', 'start_date', 'end_date', 'status', 'created',
                  'section', 'office', 'supervisor', 'ta_required', 'ta_reference_number', 'approval_date', 'is_driver',
                  'attachment_count')
        export_order = fields