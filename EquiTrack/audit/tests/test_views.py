from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import random

from django.core.management import call_command
from rest_framework import status
from mock import patch, Mock

from audit.models import Engagement
from audit.tests.base import AuditTestCaseMixin, EngagementTransitionsTestCaseMixin
from audit.tests.factories import (
    AuditFactory,
    AuditPartnerFactory,
    EngagementFactory,
    MicroAssessmentFactory,
    PartnerWithAgreementsFactory,
    PurchaseOrderFactory,
    RiskBluePrintFactory,
    RiskCategoryFactory,
    SpotCheckFactory,
    SpecialAuditFactory
)
from EquiTrack.tests.mixins import APITenantTestCase
from partners.models import PartnerType


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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_risk_ids = list(self.engagement.risks.values_list('id', flat=True))
        self.assertNotEqual(new_risk_ids, old_risk_ids)

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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
        self.forced_auth_req(
            'patch',
            '/api/audit/%s/%d/' % (self.endpoint, self.engagement.id, ),
            user=not_allowed,
            data={
                field_name: category_dict
            }
        )

        new_risk_ids = list(self.engagement.risks.values_list('id', flat=True))
        self.assertEqual(new_risk_ids, old_risk_ids)


class TestMARisksViewSet(BaseTestCategoryRisksViewSet, APITenantTestCase):
    engagement_factory = MicroAssessmentFactory
    endpoint = 'micro-assessments'

    def test_ma_risks(self):
        self._test_engagement_categories(
            category_code='ma_questionnaire', field_name='questionnaire',
            allowed_user=self.auditor
        )
        self._test_engagement_categories(
            category_code='ma_subject_areas', field_name='test_subject_areas',
            allowed_user=self.auditor
        )

    def test_update_unexisted_blueprint(self):
        self._update_unexisted_blueprint(
            field_name='questionnaire', category_code='ma_questionnaire',
            allowed_user=self.auditor
        )
        self._update_unexisted_blueprint(
            field_name='test_subject_areas', category_code='ma_subject_areas',
            allowed_user=self.auditor
        )

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

    def _test_list(self, user, engagements, params=""):
        response = self.forced_auth_req(
            'get',
            '/api/audit/engagements/',
            data={"status": params},
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertListEqual(
            sorted(map(lambda x: x['id'], response.data['results'])),
            sorted(map(lambda x: x.id, engagements))
        )

    def test_focal_point_list(self):
        self._test_list(self.unicef_focal_point, [self.engagement, self.second_engagement])

    def test_engagement_staff_list(self):
        self._test_list(self.auditor, [self.engagement])

    def test_non_engagement_staff_list(self):
        self._test_list(self.non_engagement_auditor, [])

    def test_unknown_user_list(self):
        self._test_list(self.usual_user, [])

    def test_status_filter_final(self):
        status = Engagement.STATUSES.final
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=status
        )
        self.assertEqual(self.third_engagement.status, status)
        self._test_list(self.auditor, [self.third_engagement], params=status)

    def test_status_filter_partner_contacted(self):
        status = Engagement.DISPLAY_STATUSES.partner_contacted
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted
        )
        self._test_list(
            self.auditor,
            [self.engagement, self.third_engagement],
            params=status
        )

    def test_status_filter_field_visit(self):
        status = Engagement.DISPLAY_STATUSES.field_visit
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_field_visit=datetime.date(2001, 1, 1),
        )
        self.assertIsNone(self.third_engagement.date_of_draft_report_to_ip)
        self.assertIsNotNone(self.third_engagement.date_of_field_visit)
        self._test_list(self.auditor, [self.third_engagement], params=status)

    def test_status_filter_draft_issued_to_partner(self):
        status = Engagement.DISPLAY_STATUSES.draft_issued_to_partner
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_draft_report_to_ip=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], params=status)

    def test_status_filter_comments_recieved_by_partner(self):
        status = Engagement.DISPLAY_STATUSES.comments_received_by_partner
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_comments_by_ip=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], params=status)

    def test_status_filter_draft_issued_to_unicef(self):
        status = Engagement.DISPLAY_STATUSES.draft_issued_to_unicef
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_draft_report_to_unicef=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], params=status)

    def test_status_filter_comments_received_by_unicef(self):
        status = Engagement.DISPLAY_STATUSES.comments_received_by_unicef
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_comments_by_unicef=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], params=status)


class BaseTestEngagementsCreateViewSet(EngagementTransitionsTestCaseMixin):
    endpoint = 'engagements'

    def setUp(self):
        super(BaseTestEngagementsCreateViewSet, self).setUp()
        self.create_data = {
            'end_date': self.engagement.end_date,
            'start_date': self.engagement.start_date,
            'partner_contacted_at': self.engagement.partner_contacted_at,
            'total_value': self.engagement.total_value,
            'agreement': self.engagement.agreement_id,
            'po_item': self.engagement.agreement.items.first().id,
            'partner': self.engagement.partner_id,
            'engagement_type': self.engagement.engagement_type,
            'authorized_officers': self.engagement.authorized_officers.values_list('id', flat=True),
            'staff_members': self.engagement.staff_members.values_list('id', flat=True),
            'active_pd': self.engagement.active_pd.values_list('id', flat=True),
            'shared_ip_with': self.engagement.shared_ip_with,
        }

    def _do_create(self, user, data):
        data = data or {}
        response = self.forced_auth_req(
            'post',
            self.engagements_url(),
            user=user, data=data
        )
        return response


class TestEngagementCreateActivePDViewSet(object):
    def test_partner_without_active_pd(self):
        del self.create_data['active_pd']

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('active_pd', response.data)

    def test_partner_with_active_pd(self):
        self.engagement.partner.partner_type = PartnerType.CIVIL_SOCIETY_ORGANIZATION
        self.engagement.partner.save()

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_government_partner_without_active_pd(self):
        self.engagement.partner.partner_type = PartnerType.GOVERNMENT
        self.engagement.partner.save()
        del self.create_data['active_pd']

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)


class TestMicroAssessmentCreateViewSet(TestEngagementCreateActivePDViewSet, BaseTestEngagementsCreateViewSet,
                                       APITenantTestCase):
    engagement_factory = MicroAssessmentFactory


class TestAuditCreateViewSet(TestEngagementCreateActivePDViewSet, BaseTestEngagementsCreateViewSet, APITenantTestCase):
    engagement_factory = AuditFactory


class TestSpotCheckCreateViewSet(TestEngagementCreateActivePDViewSet, BaseTestEngagementsCreateViewSet,
                                 APITenantTestCase):
    engagement_factory = SpotCheckFactory


class SpecialAuditCreateViewSet(BaseTestEngagementsCreateViewSet, APITenantTestCase):
    engagement_factory = SpecialAuditFactory

    def setUp(self):
        super(SpecialAuditCreateViewSet, self).setUp()
        self.create_data['specific_procedures'] = [
            {
                'description': sp.description,
                'finding': sp.finding,
            } for sp in self.engagement.specific_procedures.all()
        ]

    def test_engagement_with_active_pd(self):
        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_engagement_without_active_pd(self):
        del self.create_data['active_pd']

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)


class TestEngagementsUpdateViewSet(EngagementTransitionsTestCaseMixin, APITenantTestCase):
    engagement_factory = MicroAssessmentFactory

    def _do_update(self, user, data):
        data = data or {}
        response = self.forced_auth_req(
            'patch',
            '/api/audit/micro-assessments/{}/'.format(self.engagement.id),
            user=user, data=data
        )
        return response

    def test_partner_government_changed_without_pd(self):
        partner = PartnerWithAgreementsFactory(partner_type=PartnerType.GOVERNMENT)

        response = self._do_update(self.unicef_focal_point, {'partner': partner.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partner_bilaterial_changed_without_pd(self):
        partner = PartnerWithAgreementsFactory(partner_type=PartnerType.BILATERAL_MULTILATERAL)

        response = self._do_update(self.unicef_focal_point, {'partner': partner.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partner_changed_without_pd(self):
        partner = PartnerWithAgreementsFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)

        response = self._do_update(self.unicef_focal_point, {'partner': partner.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('active_pd', response.data)

    def test_partner_changed_with_pd(self):
        partner = PartnerWithAgreementsFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        response = self._do_update(
            self.unicef_focal_point,
            {
                'partner': partner.id,
                'active_pd': partner.agreements.first().interventions.values_list('id', flat=True)
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(
            map(lambda pd: pd['id'], response.data['active_pd']),
            map(lambda i: i.id, partner.agreements.first().interventions.all())
        )

    def test_government_partner_changed(self):
        partner = PartnerWithAgreementsFactory(partner_type=PartnerType.GOVERNMENT)
        response = self._do_update(self.unicef_focal_point, {'partner': partner.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_pd'], [])


class TestAuditorFirmViewSet(AuditTestCaseMixin, APITenantTestCase):
    def setUp(self):
        super(TestAuditorFirmViewSet, self).setUp()
        self.second_auditor_firm = AuditPartnerFactory()

    def _test_list_view(self, user, expected_firms):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/',
            user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(
            map(lambda x: x['id'], response.data['results']),
            map(lambda x: x.id, expected_firms)
        )

    def test_unicef_list_view(self):
        self._test_list_view(self.unicef_user, [self.auditor_firm, self.second_auditor_firm])

    def test_auditor_list_view(self):
        self._test_list_view(self.auditor, [self.auditor_firm])

    def test_usual_user_list_view(self):
        self._test_list_view(self.usual_user, [])


class TestAuditorStaffMembersViewSet(AuditTestCaseMixin, APITenantTestCase):
    def test_list_view(self):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{0}/staff-members/'.format(self.auditor_firm.id),
            user=self.unicef_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{0}/staff-members/'.format(self.auditor_firm.id),
            user=self.usual_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_view(self):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{0}/staff-members/{1}/'.format(
                self.auditor_firm.id,
                self.auditor_firm.staff_members.first().id
            ),
            user=self.unicef_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{0}/staff-members/{1}/'.format(
                self.auditor_firm.id,
                self.auditor_firm.staff_members.first().id
            ),
            user=self.usual_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_view(self):
        response = self.forced_auth_req(
            'post',
            '/api/audit/audit-firms/{0}/staff-members/'.format(
                self.auditor_firm.id,
                self.auditor_firm.staff_members.first().id
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.forced_auth_req(
            'post',
            '/api/audit/audit-firms/{0}/staff-members/'.format(
                self.auditor_firm.id,
                self.auditor_firm.staff_members.first().id
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
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_view(self):
        response = self.forced_auth_req(
            'patch',
            '/api/audit/audit-firms/{0}/staff-members/{1}/'.format(
                self.auditor_firm.id,
                self.auditor_firm.staff_members.first().id
            ),
            data={
                "user": {
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.unicef_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'patch',
            '/api/audit/audit-firms/{0}/staff-members/{1}/'.format(
                self.auditor_firm.id,
                self.auditor_firm.staff_members.first().id
            ),
            data={
                "user": {
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.usual_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestEngagementPDFExportViewSet(EngagementTransitionsTestCaseMixin, APITenantTestCase):
    engagement_factory = AuditFactory

    def _test_pdf_view(self, user, status_code=status.HTTP_200_OK):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audits/{}/pdf/'.format(self.engagement.id),
            user=user
        )

        self.assertEqual(response.status_code, status_code)
        if status_code == status.HTTP_200_OK:
            self.assertIn(response._headers['content-disposition'][0], 'Content-Disposition')

    def test_guest(self):
        self.user = None
        self._test_pdf_view(None, status.HTTP_403_FORBIDDEN)

    def test_common_user(self):
        self._test_pdf_view(self.usual_user, status.HTTP_404_NOT_FOUND)

    def test_unicef_user(self):
        self._test_pdf_view(self.unicef_user)

    def test_auditor(self):
        self._test_pdf_view(self.auditor)

    def test_focal_point(self):
        self._test_pdf_view(self.unicef_focal_point)


class TestPurchaseOrderView(AuditTestCaseMixin, APITenantTestCase):
    def setUp(self):
        super(TestPurchaseOrderView, self).setUp()
        call_command('update_audit_permissions', verbosity=0)

    def test_get_not_found(self):
        """If instance does not exist, code will attempt to sync,
        and if still does not exist then return 404
        """
        mock_sync = Mock()
        with patch("audit.views.POSynchronizer", mock_sync):
            response = self.forced_auth_req(
                "get",
                "/api/audit/purchase-orders/sync/404/",
                user=self.unicef_user,
            )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get(self):
        po = PurchaseOrderFactory(order_number="123")
        response = self.forced_auth_req(
            "get",
            "/api/audit/purchase-orders/sync/{}/".format(po.order_number),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], po.pk)


class TestEngagementPartnerView(AuditTestCaseMixin, APITenantTestCase):
    def test_get(self):
        engagement = EngagementFactory()
        response = self.forced_auth_req(
            "get",
            "/api/audit/engagements/partners/",
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], engagement.partner.pk)
