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
        ('total_value', 'Total value of selected FACE form(s) USD'),
        ('total_amount_tested', 'Total amount tested USD'),
        ('amount_refunded', 'Amount Refunded USD'),
        ('additional_supporting_documentation_provided', 'Additional Supporting Documentation Provided USD'),
        ('justification_provided_and_accepted', 'Justification Provided and Accepted USD'),
        ('write_off_required', 'Impairment USD'),
        ('pending_unsupported_amount', 'Pending Unsupported Amount USD'),
        ('high_priority_observations', 'High priority observations')
    ))
    header = labels.keys()


class FaceSpotCheckDetailCSVRenderer(BaseCSVRenderer):
    labels = OrderedDict((
        ('reference_number', 'Unique ID'),
        ('link', 'Hyperlink'),
        ('auditor', 'Auditor or Staff Assigned'),
        ('partner', 'IP'),
        ('status_display', 'Status'),
        ('total_value', 'Total value of selected FACE form(s) USD'),
        ('total_value_local', 'Total value of selected FACE form(s) Local Currency'),
        ('total_amount_tested', 'Total amount tested USD'),
        ('total_amount_tested_local', 'Total amount tested Local Currency'),
        ('amount_refunded', 'Amount Refunded USD'),
        ('amount_refunded_local', 'Amount Refunded Local Currency'),
        ('additional_supporting_documentation_provided', 'Additional Supporting Documentation Provided USD'),
        ('additional_supporting_documentation_provided_local',
         'Additional Supporting Documentation Provided Local Currency'),
        ('justification_provided_and_accepted', 'Justification Provided and Accepted USD'),
        ('justification_provided_and_accepted_local', 'Justification Provided and Accepted Local Currency'),
        ('write_off_required', 'Impairment USD'),
        ('write_off_required_local', 'Impairment Local Currency'),
        ('pending_unsupported_amount', 'Pending Unsupported Amount USD'),
        ('pending_unsupported_amount_local', 'Pending Unsupported Amount Local Currency'),
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
            ('total_value', 'Total value of selected FACE form(s) USD'),
            ('audited_expenditure', 'Audited Expenditure USD'),
            ('audited_expenditure_local', 'Audited Expenditure Local Currency'),
            ('financial_findings', 'Financial Findings USD'),
            ('financial_findings_local', 'Financial Findings Local Currency'),
            ('audit_opinion', 'Audit Opinion'),
            ('amount_refunded', 'Amount Refunded USD'),
            ('additional_supporting_documentation_provided', 'Additional Supporting Documentation Provided USD'),
            ('justification_provided_and_accepted', 'Justification Provided and Accepted USD'),
            ('write_off_required', 'Impairment USD'),
            ('pending_unsupported_amount', 'Pending Unsupported Amount USD'),
        ))
        for priority in ['high', 'medium', 'low']:
            labels['control_weaknesses.{}'.format(priority)] = 'Control Weaknesses - {}'.format(priority.capitalize())

        for blueprint in RiskCategory.objects.get(code='audit_key_weakness').blueprints.all():
            labels['subject_area.{}'.format(blueprint.id)] = 'Subject Area - {}'.format(blueprint.header)

        return labels

    @property
    def header(self):
        return self.labels.keys()


class FaceAuditDetailCSVRenderer(BaseCSVRenderer):
    @property
    def labels(self):
        labels = OrderedDict((
            ('reference_number', 'Unique ID'),
            ('link', 'Hyperlink'),
            ('auditor', 'Auditor or Staff Assigned'),
            ('partner', 'IP'),
            ('status_display', 'Status'),
            ('total_value', 'Total value of selected FACE form(s) USD'),
            ('total_value_local', 'Total value of selected FACE form(s) Local Currency'),
            ('audited_expenditure', 'Audited Expenditure USD'),
            ('audited_expenditure_local', 'Audited Expenditure Local Currency'),
            ('financial_findings', 'Financial Findings USD'),
            ('financial_findings_local', 'Financial Findings Local Currency'),
            ('audit_opinion', 'Audit Opinion'),
            ('amount_refunded', 'Amount Refunded USD'),
            ('amount_refunded_local', 'Amount Refunded Local Currency'),
            ('additional_supporting_documentation_provided', 'Additional Supporting Documentation Provided USD'),
            ('additional_supporting_documentation_provided_local', 'Additional Supporting Documentation Provided Local Currency'),
            ('justification_provided_and_accepted', 'Justification Provided and Accepted USD'),
            ('justification_provided_and_accepted_local', 'Justification Provided and Accepted Local Currency'),
            ('write_off_required', 'Impairment USD'),
            ('write_off_required_local', 'Impairment Local Currency'),
            ('pending_unsupported_amount', 'Pending Unsupported Amount USD'),
            ('pending_unsupported_amount_local', 'Pending Unsupported Amount Local Currency'),
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
            labels['subject_areas.{}'.format(blueprint.id)] = 'Tested Subject Areas v1 - {}'.format(blueprint.header)

        for blueprint in itertools.chain(*map(
            lambda c: c.blueprints.all(),
            RiskCategory.objects.get(code='ma_subject_areas_v2', parent__isnull=True).children.all()
        )):
            labels['subject_areas_v2.{}'.format(blueprint.id)] = 'Tested Subject Areas v2 - {}'.format(blueprint.header)

        for blueprint in itertools.chain(*map(
            lambda c: itertools.chain(
                itertools.chain(*map(lambda sc: sc.blueprints.all(), c.children.all())),
                c.blueprints.all()
            ),
            RiskCategory.objects.get(code='ma_questionnaire', parent__isnull=True).children.all()
        )):
            labels['questionnaire.{}'.format(blueprint.id)] = "Questionnaire v1 - {}".format(blueprint.header)

        for blueprint in itertools.chain(*map(
            lambda c: itertools.chain(
                itertools.chain(*map(lambda sc: sc.blueprints.all(), c.children.all())),
                c.blueprints.all()
            ),
            RiskCategory.objects.get(code='ma_questionnaire_v2', parent__isnull=True).children.all()
        )):
            labels['questionnaire_v2.{}'.format(blueprint.id)] = "Questionnaire v2 - {}".format(blueprint.header)

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
        ('total_value', 'Total value of selected FACE form(s) USD'),
    ))
    header = labels.keys()


class FaceSpecialAuditDetailCSVRenderer(BaseCSVRenderer):
    labels = OrderedDict((
        ('reference_number', 'Unique ID'),
        ('link', 'Hyperlink'),
        ('auditor', 'Auditor or Staff Assigned'),
        ('partner', 'IP'),
        ('status_display', 'Status'),
        ('total_value', 'Total value of selected FACE form(s) USD'),
        ('total_value_local', 'Total value of selected FACE form(s) Local Currency'),
    ))
    header = labels.keys()
