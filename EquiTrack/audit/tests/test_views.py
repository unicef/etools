import random

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from .factories import RiskCategoryFactory, RiskBluePrintFactory, \
    MicroAssessmentFactory, AuditFactory, AuditPartnerFactory
from .base import EngagementTransitionsTestCaseMixin, AuditTestCaseMixin


class BaseTestCategoryRisksViewSet(EngagementTransitionsTestCaseMixin):
    engagement_type_mapping = {
        'ma': 'microassessment',
        'audit': 'audit'
    }

    def test_list(self):
        response = self.forced_auth_req(
            'get',
            '/api/audit/%s/' % self.endpoint,
            user=self.auditor
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertTrue(isinstance(response.data['results'], list))

    def _test_engagement_categories(self, category_code, field_name, allowed_user):
        '''
        Request example:

        {
            "questionnaire": {
                "children": [
                    {
                        "id": 11,
                        "blueprints": [
                            {
                                "id": 1,
                                "risk: {
                                    "value": 4
                                }
                            },
                            {
                                "id": 2,
                                "risk": {
                                    "value": 0
                                }
                            }
                        ]
                    },
                    {
                        "id": 12,
                        "blueprints": [
                            {
                                "id": 12,
                                "risk": {
                                    "value": 4
                                }
                            }
                        ]
                    }
                ]
            }
        }
        '''
        old_risk_ids = list(self.engagement.risks.values_list('id', flat=True))

        category_dict = {
            "children": []
        }
        parent_category = RiskCategoryFactory(code=category_code)
        for i in range(0, 3):
            nested_category = RiskCategoryFactory(parent=parent_category, code=category_code)
            nested_category_data = {
                "id": nested_category.id,
                "blueprints": []
            }
            for blueprint_number in range(0, 4):
                blueprint = RiskBluePrintFactory(category=nested_category)
                nested_category_data["blueprints"].append({
                    "id": blueprint.id,
                    "risk": {
                        "value": random.randint(1, 2),
                    }
                })
            category_dict['children'].append(nested_category_data)

        response = self.forced_auth_req(
            'patch',
            '/api/audit/%s/%d/' % (self.endpoint, self.engagement.id, ),
            user=allowed_user,
            data={
                field_name: category_dict
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        new_risk_ids = list(self.engagement.risks.values_list('id', flat=True))
        self.assertNotEquals(new_risk_ids, old_risk_ids)

    def _update_unexisted_blueprint(self, field_name, category_code, allowed_user):
        category = RiskCategoryFactory(code=category_code)
        blueprint = RiskBluePrintFactory(category=category)

        data = {
            field_name: {
                "blueprints": [
                    {
                        "id": blueprint.id + 1,
                        "risk": {
                            "value": random.randint(0, 4),
                        }
                    }
                ]
            }
        }

        response = self.forced_auth_req(
            'patch',
            '/api/audit/%s/%d/' % (self.endpoint, self.engagement.id, ),
            user=allowed_user,
            data=data
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def _test_category_update_by_user_without_permissions(self, category_code, field_name, not_allowed):
        old_risk_ids = list(self.engagement.risks.values_list('id', flat=True))

        category_dict = {
            "children": []
        }
        parent_category = RiskCategoryFactory(code=category_code)
        for i in range(0, 3):
            nested_category = RiskCategoryFactory(parent=parent_category, code=category_code)
            nested_category_data = {
                "id": nested_category.id,
                "blueprints": []
            }
            for blueprint_number in range(0, 4):
                blueprint = RiskBluePrintFactory(category=nested_category)
                nested_category_data["blueprints"].append({
                    "id": blueprint.id,
                    "risk": {
                        "value": random.randint(1, 2),
                    }
                })
            category_dict['children'].append(nested_category_data)
        response = self.forced_auth_req(
            'patch',
            '/api/audit/%s/%d/' % (self.endpoint, self.engagement.id, ),
            user=not_allowed,
            data={
                field_name: category_dict
            }
        )

        new_risk_ids = list(self.engagement.risks.values_list('id', flat=True))
        self.assertEquals(new_risk_ids, old_risk_ids)


class TestMARisksViewSet(BaseTestCategoryRisksViewSet, APITenantTestCase):
    engagement_factory = MicroAssessmentFactory
    endpoint = 'micro-assessments'

    def test_ma_risks(self):
        self._test_engagement_categories(category_code='ma_questionnaire', field_name='questionnaire', allowed_user=self.auditor)
        self._test_engagement_categories(category_code='ma_subject_areas', field_name='test_subject_areas', allowed_user=self.auditor)

    def test_update_unexisted_blueprint(self):
        self._update_unexisted_blueprint(field_name='questionnaire', category_code='ma_questionnaire', allowed_user=self.auditor)
        self._update_unexisted_blueprint(field_name='test_subject_areas', category_code='ma_subject_areas', allowed_user=self.auditor)

    def test_ma_risks_update_without_perms(self):
        self._test_category_update_by_user_without_permissions(
            category_code='ma_questionnaire', field_name='questionnaire',
            not_allowed=self.unicef_focal_point
        )
        self._test_category_update_by_user_without_permissions(
            category_code='test_subject_areas', field_name='ma_subject_areas',
            not_allowed=self.unicef_focal_point
        )


class TestAuditRisksViewSet(BaseTestCategoryRisksViewSet, APITenantTestCase):
    engagement_factory = AuditFactory
    endpoint = 'audits'

    def test_audit_risks(self):
        self._test_engagement_categories(
            category_code='audit_key_weakness', field_name='key_internal_weakness',
            allowed_user=self.auditor
        )

    def test_update_unexisted_blueprint(self):
        self._update_unexisted_blueprint(
            field_name='key_internal_weakness', category_code='audit_key_weakness',
            allowed_user=self.auditor
        )

    def test_audit_risks_update_without_perms(self):
        self._test_category_update_by_user_without_permissions(
            field_name='key_internal_weakness', category_code='audit_key_weakness',
            not_allowed=self.unicef_focal_point
        )


class TestEngagementsListViewSet(EngagementTransitionsTestCaseMixin, APITenantTestCase):
    engagement_factory = MicroAssessmentFactory

    def setUp(self):
        super(TestEngagementsListViewSet, self).setUp()
        self.second_engagement = self.engagement_factory()

    def _test_list(self, user, engagements):
        response = self.forced_auth_req(
            'get',
            '/api/audit/engagements/',
            user=user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertListEqual(
            map(lambda x: x['id'], response.data['results']),
            map(lambda x: x.id, engagements)
        )

    def test_focal_point_list(self):
        self._test_list(self.unicef_focal_point, [self.engagement, self.second_engagement])

    def test_engagement_staff_list(self):
        self._test_list(self.auditor, [self.engagement])

    def test_non_engagement_staff_list(self):
        self._test_list(self.non_engagement_auditor, [])

    def test_unknown_user_list(self):
        self._test_list(self.usual_user, [])


class TestAuditOrganizationViewSet(AuditTestCaseMixin, APITenantTestCase):
    def setUp(self):
        super(TestAuditOrganizationViewSet, self).setUp()
        self.second_audit_organization = AuditPartnerFactory()

    def _test_list_view(self, user, expected_organizations):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-organizations/',
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            sorted(map(lambda x: x['id'], response.data['results'])),
            sorted(map(lambda x: x.id, expected_organizations))
        )

    def test_unicef_list_view(self):
        self._test_list_view(self.unicef_user, [self.audit_organization, self.second_audit_organization])

    def test_auditor_list_view(self):
        self._test_list_view(self.auditor, [self.audit_organization])

    def test_usual_user_list_view(self):
        self._test_list_view(self.usual_user, [])


class TestAuditOrganizationStaffMembersViewSet(AuditTestCaseMixin, APITenantTestCase):
    def test_list_view(self):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-organizations/{0}/staff-members/'.format(self.audit_organization.id),
            user=self.unicef_focal_point
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-organizations/{0}/staff-members/'.format(self.audit_organization.id),
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_view(self):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-organizations/{0}/staff-members/{1}/'.format(
                self.audit_organization.id,
                self.audit_organization.staff_members.first().id
            ),
            user=self.unicef_focal_point
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-organizations/{0}/staff-members/{1}/'.format(
                self.audit_organization.id,
                self.audit_organization.staff_members.first().id
            ),
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_view(self):
        response = self.forced_auth_req(
            'post',
            '/api/audit/audit-organizations/{0}/staff-members/'.format(
                self.audit_organization.id,
                self.audit_organization.staff_members.first().id
            ),
            data={
                "user": {
                    "email": "test_email_1@gmail.com",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.unicef_focal_point
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.forced_auth_req(
            'post',
            '/api/audit/audit-organizations/{0}/staff-members/'.format(
                self.audit_organization.id,
                self.audit_organization.staff_members.first().id
            ),
            data={
                "user": {
                    "email": "test_email_2@gmail.com",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_view(self):
        response = self.forced_auth_req(
            'patch',
            '/api/audit/audit-organizations/{0}/staff-members/{1}/'.format(
                self.audit_organization.id,
                self.audit_organization.staff_members.first().id
            ),
            data={
                "user": {
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.unicef_focal_point
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'patch',
            '/api/audit/audit-organizations/{0}/staff-members/{1}/'.format(
                self.audit_organization.id,
                self.audit_organization.staff_members.first().id
            ),
            data={
                "user": {
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
