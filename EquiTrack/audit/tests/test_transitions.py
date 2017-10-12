import random

from factory import fuzzy
from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from audit.transitions.conditions import EngagementSubmitReportRequiredFieldsCheck, SPSubmitReportRequiredFieldsCheck, \
    AuditSubmitReportRequiredFieldsCheck
from audit.tests.base import EngagementTransitionsTestCaseMixin
from audit.tests.factories import MicroAssessmentFactory, AuditFactory, SpotCheckFactory


class EngagementCheckTransitionsTestCaseMixin(object):
    fixtures = ('audit_risks_blueprints', )

    def _test_transition(self, user, action, expected_response, errors=None, data=None):
        response = self.forced_auth_req(
            'post', self._engagement_url(action), user=user, data=data
        )

        self.assertEqual(response.status_code, expected_response)
        if errors:
            self.assertListEqual(sorted(response.data.keys()), sorted(errors or []))

    def _test_submit(self, user, expected_response, errors=None, data=None):
        return self._test_transition(user, 'submit', expected_response, errors=errors, data=data)

    def _test_finalize(self, user, expected_response, errors=None, data=None):
        return self._test_transition(user, 'finalize', expected_response, errors=errors, data=data)

    def _test_cancel(self, user, expected_response, errors=None, data=None):
        return self._test_transition(user, 'cancel', expected_response, errors=errors, data=data)


class MATransitionsTestCaseMixin(EngagementTransitionsTestCaseMixin):
    engagement_factory = MicroAssessmentFactory
    endpoint = 'micro-assessments'

    def _init_filled_engagement(self):
        super(MATransitionsTestCaseMixin, self)._init_filled_engagement()
        self._fill_category('ma_questionnaire')
        self._fill_category('ma_subject_areas', extra='{"comments": "some info"}')
        self._fill_category('ma_global_assessment', extra='{"comments": "some info"}')


class AuditTransitionsTestCaseMixin(EngagementTransitionsTestCaseMixin):
    engagement_factory = AuditFactory
    endpoint = 'audits'

    def _fill_audit_specified_fields(self):
        self.engagement.audited_expenditure = random.randint(1, 22)
        self.engagement.financial_findings = random.randint(1, 22)
        self.engagement.percent_of_audited_expenditure = random.randint(1, 100)
        self.engagement.audit_opinion = fuzzy.FuzzyText(length=20).fuzz()
        self.engagement.recommendation = fuzzy.FuzzyText(length=50).fuzz()
        self.engagement.audit_observation = fuzzy.FuzzyText(length=50).fuzz()
        self.engagement.ip_response = fuzzy.FuzzyText(length=50).fuzz()
        self.engagement.save()

    def _init_filled_engagement(self):
        super(AuditTransitionsTestCaseMixin, self)._init_filled_engagement()
        self._fill_audit_specified_fields()
        self._fill_category('audit_key_weakness')


class SCTransitionsTestCaseMixin(EngagementTransitionsTestCaseMixin):
    engagement_factory = SpotCheckFactory
    endpoint = 'spot-checks'

    def _fill_sc_specified_fields(self):
        self.engagement.total_amount_tested = random.randint(1, 22)
        self.engagement.total_amount_of_ineligible_expenditure = random.randint(1, 22)
        self.engagement.internal_controls = fuzzy.FuzzyText(length=50).fuzz()
        self.engagement.save()

    def _init_filled_engagement(self):
        super(SCTransitionsTestCaseMixin, self)._init_filled_engagement()
        self._fill_sc_specified_fields()


class TestMATransitionsTestCase(EngagementCheckTransitionsTestCaseMixin, MATransitionsTestCaseMixin, APITenantTestCase):
    def test_submit_for_dummy_object(self):
        errors_fields = EngagementSubmitReportRequiredFieldsCheck.fields
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=errors_fields)

    def test_filled_questionnaire(self):
        self._fill_date_fields()
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST,
                          errors=['questionnaire', 'test_subject_areas', 'overall_risk_assessment'])

    def test_missing_comments_subject_areas(self):
        self._fill_date_fields()
        self._fill_category('ma_questionnaire')
        self._fill_category('ma_subject_areas')
        self._fill_category('ma_global_assessment')
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST,
                          errors=['test_subject_areas', 'overall_risk_assessment'])

    def test_attachments_required(self):
        self._fill_date_fields()
        self._fill_category('ma_questionnaire')
        self._fill_category('ma_subject_areas', extra='{"comments": "some info"}')
        self._fill_category('ma_global_assessment', extra='{"comments": "some info"}')
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['report_attachments'])

    def test_submit_filled_report(self):
        self._init_filled_engagement()
        self._test_submit(self.auditor, status.HTTP_200_OK)


class TestAuditTransitionsTestCase(
    EngagementCheckTransitionsTestCaseMixin, AuditTransitionsTestCaseMixin, APITenantTestCase
):
    def test_submit_for_dummy_object(self):
        errors_fields = AuditSubmitReportRequiredFieldsCheck.fields
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=errors_fields)

    def test_filled_questionnaire(self):
        self._fill_date_fields()
        self._fill_audit_specified_fields()
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['key_internal_weakness'])

    def test_attachments_required(self):
        self._fill_date_fields()
        self._fill_audit_specified_fields()
        self._fill_category('audit_key_weakness')
        self._test_submit(self.auditor, status.HTTP_400_BAD_REQUEST, errors=['report_attachments'])

    def test_submit_filled_report(self):
        self._init_filled_engagement()
        self._test_submit(self.auditor, status.HTTP_200_OK)


class TestSCTransitionsTestCase(
    EngagementCheckTransitionsTestCaseMixin, SCTransitionsTestCaseMixin, APITenantTestCase
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

    def test_finalize_focal_point(self):
        self._init_submitted_engagement()
        self._test_finalize(self.unicef_focal_point, status.HTTP_200_OK)

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
        self._test_cancel(self.unicef_focal_point, status.HTTP_200_OK, data={'cancel_comment': 'cancel_comment'})

    def test_cancel_finalized_focal_point(self):
        self._init_finalized_engagement()
        self._test_cancel(self.unicef_focal_point, status.HTTP_403_FORBIDDEN)


class EngagementCheckTransitionsMetadataTestCaseMixin(object):
    def _test_allowed_actions(self, user, actions):
        response = self.forced_auth_req(
            'options', self._engagement_url(), user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            sorted(map(
                lambda t: t['code'],
                response.data['actions']['allowed_FSM_transitions']
            )),
            sorted(actions)
        )


class TestSCTransitionsMetadataTestCase(
    EngagementCheckTransitionsMetadataTestCaseMixin, SCTransitionsTestCaseMixin, APITenantTestCase
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
        self._test_allowed_actions(self.unicef_focal_point, ['finalize', 'cancel'])

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
