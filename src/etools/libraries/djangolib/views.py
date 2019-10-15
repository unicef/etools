from datetime import date


class ExportFilenameMixin:

    def export_content_dispostion(self, basename):
        today = ':{%Y-%b-%d}'.format(date.today())
        country_code = self.request.tenant.country_short_code
        filename = f'{basename}_{today}_{country_code}'
        return f'attachment;filename={filename}.csv'
