import random
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType

from factory import fuzzy
from rest_framework import status
from unicef_attachments.models import Attachment

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.audit.models import Finding, SpecificProcedure
from etools.applications.audit.tests.base import EngagementTransitionsTestCaseMixin
from etools.applications.audit.tests.factories import (
    AuditFactory,
    FindingFactory,
    KeyInternalControlFactory,
    MicroAssessmentFactory,
    SpecialAuditFactory,
    SpotCheckFactory,
)
from etools.applications.audit.transitions.conditions import (
    AuditSubmitReportRequiredFieldsCheck,
    EngagementSubmitReportRequiredFieldsCheck,
    SPSubmitReportRequiredFieldsCheck,
)
from etools.applications.core.tests.cases import BaseTenantTestCase


class EngagementCheckTransitionsTestCaseMixin:
    fixtures = ('audit_risks_blueprints', )

    def _test_transition(self, user, action, expected_response, errors=None, data=None):
        response = self.forced_auth_req(
            'post', self.engagement_url(action), user=user, data=data
        )

        self.assertEqual(response.status_code, expected_response)
        if errors:
            self.assertListEqual(list(response.data.keys()), errors or [])

    def _test_submit(self, user, expected_response, errors=None, data=None):
        return self._test_transition(user, 'submit', expected_response, errors=errors, data=data)

    def _test_send_back(self, user, expected_response, errors=None, data=None):
        return self._test_transition(user, 'send_back', expected_response, errors=errors, data=data)

    def _test_finalize(self, user, expected_response, errors=None, data=None):
        return self._test_transition(user, 'finalize', expected_response, errors=errors, data=data)

    def _test_cancel(self, user, expected_response, errors=None, data=None):
        return self._test_transition(user, 'cancel', expected_response, errors=errors, data=data)


class MATransitionsTestCaseMixin(EngagementTransitionsTestCaseMixin):
    engagement_factory = MicroAssessmentFactory
    endpoint = 'micro-assessments'

    def _init_filled_engagement(self):
        super()._init_filled_engagement()
        self._fill_category('ma_questionnaire_v2')
        self._fill_category('ma_subject_areas_v2', extra={"comments": "some info"})
        self._fill_category('ma_global_assessment', extra={"comments": "some info"})


class AuditTransitionsTestCaseMixin(EngagementTransitionsTestCaseMixin):
    engagement_factory = AuditFactory
    endpoint = 'audits'

    def _fill_audit_specified_fields(self):
        self.engagement.audited_expenditure = random.randint(1, 22)
        self.engagement.financial_findings = random.randint(1, 22)
        self.engagement.audit_opinion = fuzzy.FuzzyText(length=20).fuzz()
        self.engagement.exchange_rate = fuzzy.FuzzyDecimal(0.5, 400).fuzz()
        self.engagement.currency_of_report = 'USD'
        self.engagement.key_internal_controls.add(
            *[KeyInternalControlFactory(audit=self.engagement) for _ in range(3)])
        self.engagement.save()

    def _init_filled_engagement(self):
        super()._init_filled_engagement()
        self._fill_audit_specified_fields()
        self._fill_category('audit_key_weakness')


class SpecialAuditTransitionsTestCaseMixin(EngagementTransitionsTestCaseMixin):
    engagement_factory = SpecialAuditFactory
    endpoint = 'special-audits'

    def _init_specific_procedure(self):
        SpecificProcedure(audit=self.engagement, description=fuzzy.FuzzyText(length=20).fuzz()).save()

    def _fill_specific_procedure(self):
        for sp in self.engagement.specific_procedures.all():
            sp.finding = 'Test'
            sp.save()

    def _init_filled_engagement(self):
        super()._init_filled_engagement()
        self._init_specific_procedure()
        self._fill_specific_procedure()


class SCTransitionsTestCaseMixin(EngagementTransitionsTestCaseMixin):
    engagement_factory = SpotCheckFactory
    endpoint = 'spot-checks'

    def _fill_sc_specified_fields(self):
        self.engagement.total_amount_tested = random.randint(1, 22)
        self.engagement.total_amount_of_ineligible_expenditure = random.randint(1, 22)
        self.engagement.internal_controls = fuzzy.FuzzyText(length=50).fuzz()
        self.engagement.exchange_rate = fuzzy.FuzzyDecimal(0.5, 400).fuzz()
        self.engagement.currency_of_report = 'USD'
        self.engagement.save()

    def _init_filled_engagement(self):
        super()._init_filled_engagement()
        self._fill_sc_specified_fields()


class TestMATransitionsTestCase(
        EngagementCheckTransitionsTestCaseMixin,
        MATransitionsTestCaseMixin,
        BaseTenantTestCase
):
    def test_submit_for_dummy_object(self):
        errors_fields = EngagementSubmitReportRequiredFieldsCheck.fields
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=errors_fields)

    def test_filled_questionnaire(self):
        self._fill_date_fields()
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST,
                          errors=['overall_risk_assessment', 'questionnaire', 'test_subject_areas'])

    def test_missing_comments_subject_areas(self):
        self._fill_date_fields()
        self._fill_category('ma_questionnaire_v2')
        self._fill_category('ma_subject_areas_v2')
        self._fill_category('ma_global_assessment')
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST,
                          errors=['overall_risk_assessment', 'test_subject_areas'])

    def test_attachments_required(self):
        self._fill_date_fields()
        self._fill_category('ma_questionnaire_v2')
        self._fill_category('ma_subject_areas_v2', extra={"comments": "some info"})
        self._fill_category('ma_global_assessment', extra={"comments": "some info"})
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['report_attachments'])

    def test_submit_filled_report(self):
        self._init_filled_engagement()
        self._test_submit(self.auditor, status.HTTP_200_OK)


class TestAuditTransitionsTestCase(
    EngagementCheckTransitionsTestCaseMixin, AuditTransitionsTestCaseMixin, BaseTenantTestCase
):
    def test_submit_for_dummy_object(self):
        errors_fields = AuditSubmitReportRequiredFieldsCheck.fields
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=errors_fields)

    def test_unfilled_questionnaire(self):
        self._fill_date_fields()
        self._fill_audit_specified_fields()
        # no key internal weaknesses added
        self._add_attachment('audit_report', name='report')
        self._test_submit(self.auditor, status.HTTP_200_OK)

    def test_attachments_required(self):
        self._fill_date_fields()
        self._fill_audit_specified_fields()
        self._fill_category('audit_key_weakness')
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['report_attachments'])

    def test_submit_filled_report(self):
        self._init_filled_engagement()
        self._test_submit(self.auditor, status.HTTP_200_OK)


class TestSATransitionsTestCase(
    EngagementCheckTransitionsTestCaseMixin, SpecialAuditTransitionsTestCaseMixin, BaseTenantTestCase
):
    def test_submit_for_dummy_object(self):
        errors_fields = EngagementSubmitReportRequiredFieldsCheck.fields
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=errors_fields)

    def test_submit_without_finding_object(self):
        self._fill_date_fields()
        self._init_specific_procedure()
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['specific_procedures'])

    def test_attachments_required(self):
        self._fill_date_fields()
        self._init_specific_procedure()
        self._fill_specific_procedure()
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['report_attachments'])

    def test_success_submit(self):
        self._init_filled_engagement()
        self._test_submit(self.auditor, status.HTTP_200_OK)


class TestSCTransitionsTestCase(
    EngagementCheckTransitionsTestCaseMixin, SCTransitionsTestCaseMixin, BaseTenantTestCase
):
    def test_submit_for_dummy_object(self):
        errors_fields = SPSubmitReportRequiredFieldsCheck.fields
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=errors_fields)

    def test_submit_attachments_required(self):
        self._fill_date_fields()
        self._fill_sc_specified_fields()
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['report_attachments'])

    def test_submit_filled_report(self):
        self._init_filled_engagement()
        self._test_submit(self.auditor, status.HTTP_200_OK)

    def test_submit_filled_report_focal_point(self):
        self._init_filled_engagement()
        self._test_submit(self.unicef_focal_point, status.HTTP_403_FORBIDDEN)

    def test_finalize_auditor(self):
        self._init_submitted_engagement()
        self._test_finalize(self.auditor, status.HTTP_403_FORBIDDEN)

    def test_finalize_focal_point_high_priority_findings(self):
        self._init_submitted_engagement()
        FindingFactory(spot_check=self.engagement, priority=Finding.PRIORITIES.high)
        self._test_finalize(self.unicef_focal_point, status.HTTP_400_BAD_REQUEST)

    def test_finalize_focal_point(self):
        self._init_submitted_engagement()
        content_type = ContentType.objects.get_for_model(self.engagement)
        code = 'spot_check_final_report'
        attachment_qs = Attachment.objects.filter(
            code=code,
            content_type=content_type,
            object_id=self.engagement.pk,
        )
        FindingFactory(spot_check=self.engagement, priority=Finding.PRIORITIES.high)
        ActionPointFactory(engagement=self.engagement, high_priority=True)
        with patch(self.filepath, self.mock_filepath):
            self._test_finalize(self.unicef_focal_point, status.HTTP_200_OK)
        self.assertTrue(attachment_qs.exists())
        attachment = attachment_qs.get()
        assert attachment.file
        self.assertEqual(attachment.file_type.group, [code])

    def test_cancel_auditor(self):
        self._test_cancel(self.auditor, status.HTTP_403_FORBIDDEN)

    def test_cancel_focal_point_without_msg(self):
        self._test_cancel(self.unicef_focal_point, status.HTTP_400_BAD_REQUEST, errors=['cancel_comment'])

    def test_cancel_focal_point(self):
        self._test_cancel(self.unicef_focal_point, status.HTTP_200_OK, data={'cancel_comment': 'cancel_comment'})

    def test_cancel_submitted_auditor(self):
        self._init_submitted_engagement()
        self._test_cancel(self.auditor, status.HTTP_403_FORBIDDEN)

    def test_cancel_submitted_focal_point(self):
        self._init_submitted_engagement()
        self._test_cancel(self.unicef_focal_point, status.HTTP_403_FORBIDDEN)

    def test_cancel_finalized_focal_point(self):
        self._init_finalized_engagement()
        self._test_cancel(self.unicef_focal_point, status.HTTP_403_FORBIDDEN)


class EngagementCheckTransitionsMetadataTestCaseMixin:
    def _test_allowed_actions(self, user, actions):
        response = self.forced_auth_req(
            'options', self.engagement_url(), user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_codes = [action['code'] for action in response.data['actions']['allowed_FSM_transitions']]
        self.assertListEqual(action_codes, actions)


class TestSCTransitionsMetadataTestCase(
    EngagementCheckTransitionsMetadataTestCaseMixin, SCTransitionsTestCaseMixin, BaseTenantTestCase
):
    def test_created_auditor(self):
        self._test_allowed_actions(self.auditor, ['submit'])

    def test_created_focal_point(self):
        self._test_allowed_actions(self.unicef_focal_point, ['cancel'])

    def test_submitted_auditor(self):
        self._init_submitted_engagement()
        self._test_allowed_actions(self.auditor, [])

    def test_submitted_focal_point(self):
        self._init_submitted_engagement()
        self._test_allowed_actions(self.unicef_focal_point, ['finalize', 'send_back'])

    def test_finalized_auditor(self):
        self._init_finalized_engagement()
        self._test_allowed_actions(self.auditor, [])

    def test_finalized_focal_point(self):
        self._init_finalized_engagement()
        self._test_allowed_actions(self.unicef_focal_point, [])

    def test_cancelled_auditor(self):
        self._init_cancelled_engagement()
        self._test_allowed_actions(self.auditor, [])

    def test_cancelled_focal_point(self):
        self._init_cancelled_engagement()
        self._test_allowed_actions(self.unicef_focal_point, [])
