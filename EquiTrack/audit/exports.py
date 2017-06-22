from rest_framework_csv.renderers import CSVRenderer

from .serializers import AuditorFirmExportSerializer, EngagementExportSerializer


class BaseCSVRenderer(CSVRenderer):
    def render(self, data, *args, **kwargs):
        if 'results' in data:
            data = data['results']
        return super(BaseCSVRenderer, self).render(data, *args, **kwargs)


class AuditorFirmCSVRenderer(BaseCSVRenderer):
    header = AuditorFirmExportSerializer.Meta.fields
    labels = {h: h.capitalize() for h in header}


class EngagementCSVRenderer(BaseCSVRenderer):
    header = EngagementExportSerializer.Meta.fields
    labels = {h: h.capitalize() for h in header}
