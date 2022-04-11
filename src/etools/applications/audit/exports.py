import itertools
from collections import OrderedDict

from rest_framework_csv.renderers import CSVRenderer

from etools.applications.audit.models import RiskCategory
from etools.applications.audit.serializers.auditor import AuditorFirmExportSerializer
from etools.applications.audit.serializers.engagement import EngagementExportSerializer


class BaseCSVRenderer(CSVRenderer):
    def render(self, data, *args, **kwargs):
        if 'results' in data:
            data = data['results']
        return super().render(data, *args, **kwargs)


class AuditorFirmCSVRenderer(BaseCSVRenderer):
    header = AuditorFirmExportSerializer.Meta.fields
    labels = {h: h.capitalize() for h in header}


class EngagementCSVRenderer(BaseCSVRenderer):
    header = EngagementExportSerializer.Meta.fields
    labels = {h: h.capitalize() for h in header}


class SpotCheckDetailCSVRenderer(BaseCSVRenderer):
    labels = OrderedDict((
        ('reference_number', 'Unique ID'),
        ('link', 'Hyperlink'),
        ('auditor', 'Auditor or Staff Assigned'),
        ('partner', 'IP'),
        ('status_display', 'Status'),
        ('total_value', 'Total value of selected FACE form(s)'),
        ('total_amount_tested', 'Total amount tested'),
        ('amount_refunded', 'Amount Refunded'),
        ('additional_supporting_documentation_provided', 'Additional Supporting Documentation Provided'),
        ('justification_provided_and_accepted', 'Justification Provided and Accepted'),
        ('write_off_required', 'Impairment'),
        ('pending_unsupported_amount', 'Pending Unsupported Amount'),
        ('high_priority_observations', 'High priority observations')
    ))
    header = labels.keys()


class AuditDetailCSVRenderer(BaseCSVRenderer):
    @property
    def labels(self):
        labels = OrderedDict((
            ('reference_number', 'Unique ID'),
            ('link', 'Hyperlink'),
            ('auditor', 'Auditor or Staff Assigned'),
            ('partner', 'IP'),
            ('status_display', 'Status'),
            ('total_value', 'Total value of selected FACE form(s)'),
            ('audited_expenditure', 'Audited Expenditure'),
            ('financial_findings', 'Financial Findings'),
            ('audited_expenditure_local', 'Audited Expenditure Local Currency'),
            ('financial_findings_local', 'Financial Findings Local Currency'),
            ('audit_opinion', 'Audit Opinion'),
            ('amount_refunded', 'Amount Refunded'),
            ('additional_supporting_documentation_provided', 'Additional Supporting Documentation Provided'),
            ('justification_provided_and_accepted', 'Justification Provided and Accepted'),
            ('write_off_required', 'Impairment'),
            ('pending_unsupported_amount', 'Pending Unsupported Amount'),
        ))
        for priority in ['high', 'medium', 'low']:
            labels['control_weaknesses.{}'.format(priority)] = 'Control Weaknesses - {}'.format(priority.capitalize())

        for blueprint in RiskCategory.objects.get(code='audit_key_weakness').blueprints.all():
            labels['subject_area.{}'.format(blueprint.id)] = 'Subject Area - {}'.format(blueprint.header)

        return labels

    @property
    def header(self):
        return self.labels.keys()


class MicroAssessmentDetailCSVRenderer(BaseCSVRenderer):
    @property
    def labels(self):
        labels = OrderedDict((
            ('reference_number', 'Unique ID'),
            ('link', 'Hyperlink'),
            ('auditor', 'Auditor or Staff Assigned'),
            ('partner', 'IP'),
            ('status_display', 'Status'),
            ('overall_risk_assessment', 'Overall Risk Assessment'),
        ))

        for blueprint in itertools.chain(*map(
            lambda c: c.blueprints.all(),
            RiskCategory.objects.get(code='ma_subject_areas', parent__isnull=True).children.all()
        )):
            labels['subject_areas.{}'.format(blueprint.id)] = 'Tested Subject Areas - {}'.format(blueprint.header)

        for blueprint in itertools.chain(*map(
            lambda c: itertools.chain(
                itertools.chain(*map(lambda sc: sc.blueprints.all(), c.children.all())),
                c.blueprints.all()
            ),
            RiskCategory.objects.get(code='ma_questionnaire', parent__isnull=True).children.all()
        )):
            labels['questionnaire.{}'.format(blueprint.id)] = blueprint.header

        return labels

    @property
    def header(self):
        return self.labels.keys()


class SpecialAuditDetailCSVRenderer(BaseCSVRenderer):
    labels = OrderedDict((
        ('reference_number', 'Unique ID'),
        ('link', 'Hyperlink'),
        ('auditor', 'Auditor or Staff Assigned'),
        ('partner', 'IP'),
        ('status_display', 'Status'),
    ))
    header = labels.keys()
