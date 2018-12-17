from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer

from etools.applications.field_monitoring.shared.models import FMMethod


class CheckListCSVRenderer(CSVRenderer):
    @property
    def labels(self):
        methods = FMMethod.objects.all()

        labels = {
            'cp_output': _('CP Output'),
            'category': _('Category'),
            'checklist_item': _('Checklist Item'),
            'by_partner': _('By Partner'),
            'specific_details': _('Specific Details'),
        }

        for m in methods:
            labels['selected_methods.{}'.format(m.name)] = m.name

        for m in methods:
            if not m.is_types_applicable:
                continue

            labels['recommended_method_types.{}'.format(m.name)] = _('Rec. {} types').format(m.name)

        return labels

    @property
    def header(self):
        return self.labels.keys()
