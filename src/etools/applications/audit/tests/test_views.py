import datetime
import json
import random
from copy import copy
from decimal import Decimal
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from factory import fuzzy
from rest_framework import status
from unicef_attachments.models import Attachment

from etools.applications.action_points.tests.factories import ActionPointCategoryFactory, ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.audit.models import Audit, Auditor, Engagement, Risk, SpecialAudit, SpotCheck, UNICEFUser
from etools.applications.audit.tests.base import AuditTestCaseMixin, EngagementTransitionsTestCaseMixin
from etools.applications.audit.tests.factories import (
    AuditFactory,
    AuditFocalPointUserFactory,
    AuditorUserFactory,
    AuditPartnerFactory,
    EngagementFactory,
    MicroAssessmentFactory,
    PartnerWithAgreementsFactory,
    PurchaseOrderFactory,
    RiskBluePrintFactory,
    RiskCategoryFactory,
    SpecialAuditFactory,
    SpotCheckFactory,
    StaffSpotCheckFactory,
    UserFactory,
)
from etools.applications.audit.tests.test_transitions import MATransitionsTestCaseMixin, SCTransitionsTestCaseMixin
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, OfficeFactory, RealmFactory


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

    def _test_engagement_categories(self, category_code, field_name, allowed_user, many=False):
        """
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
        """
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
                blueprint_data = {
                    "id": blueprint.id,
                }
                risk_data = {
                    "value": random.randint(1, 2),
                }
                if not many:
                    blueprint_data['risk'] = risk_data
                else:
                    blueprint_data['risks'] = [risk_data]

                nested_category_data["blueprints"].append(blueprint_data)
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

    def _update_unexisted_blueprint(self, field_name, category_code, allowed_user, many=False):
        category = RiskCategoryFactory(code=category_code)
        blueprint = RiskBluePrintFactory(category=category)

        blueprint_data = {
            "id": blueprint.id + 1,
        }
        risk_data = {
            "value": random.randint(1, 2),
        }
        if not many:
            blueprint_data['risk'] = risk_data
        else:
            blueprint_data['risks'] = [risk_data]

        data = {
            field_name: {
                "blueprints": [blueprint_data]
            }
        }

        response = self.forced_auth_req(
            'patch',
            '/api/audit/%s/%d/' % (self.endpoint, self.engagement.id, ),
            user=allowed_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def _test_category_update_by_user_without_permissions(self, category_code, field_name, not_allowed, many=False):
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
                blueprint_data = {
                    "id": blueprint.id,
                }
                risk_data = {
                    "value": random.randint(1, 2),
                }
                if not many:
                    blueprint_data['risk'] = risk_data
                else:
                    blueprint_data['risks'] = [risk_data]

                nested_category_data["blueprints"].append(blueprint_data)
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


class TestMARisksViewSet(BaseTestCategoryRisksViewSet, BaseTenantTestCase):
    engagement_factory = MicroAssessmentFactory
    endpoint = 'micro-assessments'

    def test_ma_risks_v1(self):
        self.engagement.questionnaire_version = 1
        self.engagement.save()
        self._test_engagement_categories(
            category_code='ma_questionnaire', field_name='questionnaire',
            allowed_user=self.auditor
        )
        self._test_engagement_categories(
            category_code='ma_subject_areas', field_name='test_subject_areas',
            allowed_user=self.auditor
        )

    def test_ma_risks(self):
        self._test_engagement_categories(
            category_code='ma_questionnaire_v2', field_name='questionnaire',
            allowed_user=self.auditor
        )
        self._test_engagement_categories(
            category_code='ma_subject_areas_v2', field_name='test_subject_areas',
            allowed_user=self.auditor
        )

    def test_update_unexisted_blueprint_v1(self):
        self.engagement.questionnaire_version = 1
        self.engagement.save()
        self._update_unexisted_blueprint(
            field_name='questionnaire', category_code='ma_questionnaire',
            allowed_user=self.auditor
        )
        self._update_unexisted_blueprint(
            field_name='test_subject_areas', category_code='ma_subject_areas',
            allowed_user=self.auditor
        )

    def test_update_unexisted_blueprint(self):
        self._update_unexisted_blueprint(
            field_name='questionnaire', category_code='ma_questionnaire_v2',
            allowed_user=self.auditor
        )
        self._update_unexisted_blueprint(
            field_name='test_subject_areas', category_code='ma_subject_areas_v2',
            allowed_user=self.auditor
        )

    def test_ma_risks_update_without_perms_v1(self):
        self.engagement.questionnaire_version = 1
        self.engagement.save()
        self._test_category_update_by_user_without_permissions(
            category_code='ma_questionnaire', field_name='questionnaire',
            not_allowed=self.unicef_focal_point
        )
        self._test_category_update_by_user_without_permissions(
            category_code='test_subject_areas', field_name='ma_subject_areas',
            not_allowed=self.unicef_focal_point
        )

    def test_ma_risks_update_without_perms(self):
        self._test_category_update_by_user_without_permissions(
            category_code='ma_questionnaire_v2', field_name='questionnaire',
            not_allowed=self.unicef_focal_point
        )
        self._test_category_update_by_user_without_permissions(
            category_code='test_subject_areas', field_name='ma_subject_areas',
            not_allowed=self.unicef_focal_point
        )


class TestAuditRisksViewSet(BaseTestCategoryRisksViewSet, BaseTenantTestCase):
    engagement_factory = AuditFactory
    endpoint = 'audits'

    def test_audit_risks(self):
        self._test_engagement_categories(
            category_code='audit_key_weakness', field_name='key_internal_weakness',
            allowed_user=self.auditor, many=True
        )

    def test_update_unexisted_blueprint(self):
        self._update_unexisted_blueprint(
            field_name='key_internal_weakness', category_code='audit_key_weakness',
            allowed_user=self.auditor, many=True
        )

    def test_audit_risks_update_without_perms(self):
        self._test_category_update_by_user_without_permissions(
            field_name='key_internal_weakness', category_code='audit_key_weakness',
            not_allowed=self.unicef_focal_point, many=True
        )


class TestEngagementsListViewSet(EngagementTransitionsTestCaseMixin, BaseTenantTestCase):
    engagement_factory = MicroAssessmentFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.second_engagement = cls.engagement_factory()

    def _test_list(self, user, engagements=None, filter_params=None, expected_status=status.HTTP_200_OK):
        response = self.forced_auth_req(
            'get',
            '/api/audit/engagements/',
            data=filter_params or {},
            user=user
        )
        self.assertEqual(response.status_code, expected_status)

        if not response.status_code == status.HTTP_200_OK:
            return

        self.assertIn('results', response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertCountEqual(
            map(lambda x: x['id'], response.data['results']),
            map(lambda x: x.id, engagements or [])
        )

    def test_focal_point_list(self):
        self._test_list(self.unicef_focal_point, [self.engagement, self.second_engagement])

    def test_engagement_staff_list(self):
        self._test_list(self.auditor, [self.engagement])

    def test_engagement_staff_list_multiple_auditor_realms(self):
        auditor_firm_1 = AuditPartnerFactory()
        engagement_1 = self.engagement_factory(agreement__auditor_firm=auditor_firm_1, staff_members=[self.auditor])
        RealmFactory(
            user=self.auditor, country=CountryFactory(),
            organization=auditor_firm_1.organization, group=GroupFactory(name="Auditor")
        )
        self._test_list(self.auditor, [self.engagement])

        self.auditor.profile.organization = auditor_firm_1.organization
        self.auditor.profile.save(update_fields=['organization'])
        self._test_list(self.auditor, [engagement_1])

    def test_non_engagement_staff_list(self):
        self._test_list(self.non_engagement_auditor, [])

    def test_unknown_user_list(self):
        self._test_list(self.usual_user, expected_status=status.HTTP_403_FORBIDDEN)

    def test_list_view_without_audit_organization(self):
        user = UserFactory(realms__data=[Auditor.name, UNICEFUser.name])

        self._test_list(user, [self.engagement, self.second_engagement])

    def test_status_filter_final(self):
        status = Engagement.STATUSES.final
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=status
        )
        self.assertEqual(self.third_engagement.status, status)
        self._test_list(self.auditor, [self.third_engagement], filter_params={'status': status})

    def test_status_filter_partner_contacted(self):
        status = Engagement.DISPLAY_STATUSES.partner_contacted
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted
        )
        self._test_list(
            self.auditor,
            [self.engagement, self.third_engagement],
            filter_params={'status': status}
        )

    def test_status_filter_multiple(self):
        engagement_audit = AuditFactory(
            agreement__auditor_firm=self.auditor_firm,
        )
        engagement_special_audit = SpecialAuditFactory(
            agreement__auditor_firm=self.auditor_firm,
        )
        self._test_list(
            self.auditor,
            [engagement_audit, engagement_special_audit],
            filter_params={
                'engagement_type__in': ",".join(
                    [Engagement.TYPE_AUDIT, Engagement.TYPE_SPECIAL_AUDIT]
                )
            }
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
        self._test_list(self.auditor, [self.third_engagement], filter_params={'status': status})

    def test_status_filter_draft_issued_to_partner(self):
        status = Engagement.DISPLAY_STATUSES.draft_issued_to_partner
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_draft_report_to_ip=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], filter_params={'status': status})

    def test_status_filter_comments_recieved_by_partner(self):
        status = Engagement.DISPLAY_STATUSES.comments_received_by_partner
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_comments_by_ip=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], filter_params={'status': status})

    def test_status_filter_draft_issued_to_unicef(self):
        status = Engagement.DISPLAY_STATUSES.draft_issued_to_unicef
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_draft_report_to_unicef=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], filter_params={'status': status})

    def test_status_filter_comments_received_by_unicef(self):
        status = Engagement.DISPLAY_STATUSES.comments_received_by_unicef
        self.third_engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            status=Engagement.STATUSES.partner_contacted,
            date_of_comments_by_unicef=datetime.date(2001, 1, 1),
        )
        self._test_list(self.auditor, [self.third_engagement], filter_params={'status': status})

    def test_hact_view(self):
        self._init_finalized_engagement()

        response = self.forced_auth_req(
            'get',
            '/api/audit/engagements/hact/',
            data={'partner': self.engagement.partner.id},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotEqual(response.data[0], {})
        self.assertEqual(response.data[0]['open_high_priority_count'], 0)

    def test_hact_view_open_high_priority_count(self):
        self._init_finalized_engagement()
        ActionPointFactory(engagement=self.engagement, status='open', high_priority=True)

        response = self.forced_auth_req(
            'get',
            '/api/audit/engagements/hact/',
            data={'partner': self.engagement.partner.id},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotEqual(response.data[0], {})
        self.assertEqual(response.data[0]['open_high_priority_count'], 1)

    def test_csv_view(self):
        AuditFactory()
        MicroAssessmentFactory()
        SpotCheckFactory()

        response = self.forced_auth_req(
            'get',
            '/api/audit/engagements/csv/',
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])

    def test_staff_spot_checks_csv_view(self):
        StaffSpotCheckFactory()

        response = self.forced_auth_req(
            'get',
            '/api/audit/staff-spot-checks/csv/',
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])

    def test_search_by_id(self):
        self._test_list(self.auditor, [self.engagement], filter_params={'search': self.engagement.pk})
        self._test_list(self.auditor, filter_params={'search': -1})

    def test_search_by_vendor_number(self):
        organization = OrganizationFactory(vendor_number="321")
        partner = PartnerWithAgreementsFactory(organization=organization)
        engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            partner=partner,
        )
        self.assertTrue(partner.vendor_number)
        self._test_list(
            self.auditor,
            [engagement],
            filter_params={'search': engagement.partner.vendor_number},
        )

    def test_search_by_short_name(self):
        organization = OrganizationFactory(short_name="shorty")
        partner = PartnerWithAgreementsFactory(organization=organization)
        engagement = self.engagement_factory(
            agreement__auditor_firm=self.auditor_firm,
            partner=partner,
        )
        self.assertTrue(partner.short_name)
        self._test_list(
            self.auditor,
            [engagement],
            filter_params={'search': engagement.partner.short_name},
        )


class BaseTestEngagementsCreateViewSet(EngagementTransitionsTestCaseMixin):
    endpoint = 'engagements'

    def setUp(self):
        super().setUp()
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
            'users_notified': self.engagement.users_notified.values_list('id', flat=True),
            'staff_members': self.engagement.staff_members.values_list('id', flat=True),
            'active_pd': self.engagement.active_pd.values_list('id', flat=True),
            'shared_ip_with': self.engagement.shared_ip_with,
        }
        if self.create_data['engagement_type'] in [Engagement.TYPE_AUDIT, Engagement.TYPE_SPOT_CHECK]:
            self.create_data['face_forms'] = [
                {
                    "commitment_ref": "123",
                    "start_date": "2025-07-11",
                    "end_date": "2025-07-11",
                    "dct_amt_usd": "321.00",
                    "dct_amt_local": "222.00"
                }
            ]

    def _do_create(self, user, data):
        data = data or {}
        for date_field in [
            'start_date', 'end_date', 'partner_contacted_at',
            'date_of_field_visit', 'date_of_draft_report_to_ip',
            'date_of_comments_by_ip', 'date_of_draft_report_to_unicef',
            'date_of_comments_by_unicef'
        ]:
            if data.get(date_field):
                if isinstance(data[date_field], datetime.datetime):
                    data[date_field] = data[date_field].date()
                data[date_field] = data[date_field].isoformat()
        response = self.forced_auth_req(
            'post',
            self.engagements_url(),
            user=user, data=data
        )
        return response


class TestEngagementCreateActivePDViewSet:
    def test_partner_without_active_pd(self):
        del self.create_data['active_pd']

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['active_pd'], [])

    def test_partner_with_active_pd(self):
        self.engagement.partner.partner_type = OrganizationType.CIVIL_SOCIETY_ORGANIZATION
        self.engagement.partner.save()

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_government_partner_without_active_pd(self):
        self.engagement.partner.partner_type = OrganizationType.GOVERNMENT
        self.engagement.partner.save()
        del self.create_data['active_pd']

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_attachments(self):
        file_type_engagement = AttachmentFileTypeFactory(
            code="audit_engagement",
        )
        attachment_engagement = AttachmentFactory(
            file="test_engagement.pdf",
            file_type=None,
            code="",
        )
        self.create_data["engagement_attachments"] = attachment_engagement.pk

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = json.loads(response.content)
        engagement_val = data["engagement_attachments"]
        self.assertIsNotNone(engagement_val)
        self.assertTrue(
            engagement_val.endswith(attachment_engagement.file.name)
        )
        attachment_engagement.refresh_from_db()
        self.assertEqual(attachment_engagement.file_type, file_type_engagement)


class TestMicroAssessmentCreateViewSet(TestEngagementCreateActivePDViewSet, BaseTestEngagementsCreateViewSet,
                                       BaseTenantTestCase):
    engagement_factory = MicroAssessmentFactory

    def test_partner_contacted_at_validation(self):
        # date should be in past
        data = copy(self.create_data)
        data['partner_contacted_at'] = datetime.datetime.now() + datetime.timedelta(days=1)
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('partner_contacted_at', response.data)


class TestAuditCreateViewSet(TestEngagementCreateActivePDViewSet, BaseTestEngagementsCreateViewSet, BaseTenantTestCase):
    engagement_factory = AuditFactory

    def setUp(self):
        super().setUp()
        self.create_data['year_of_audit'] = timezone.now().year

    def test_end_date_validation(self):
        data = copy(self.create_data)
        data['end_date'] = data['start_date'] - datetime.timedelta(days=1)
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)

    def test_partner_contacted_at_validation(self):
        data = copy(self.create_data)
        data['partner_contacted_at'] = data['end_date'] - datetime.timedelta(days=1)
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('partner_contacted_at', response.data)

    def test_face_form_validation(self):
        data = copy(self.create_data)
        data['face_forms'] = []
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You must specify at least one FACE Form.', response.data['non_field_errors'])

    def test_with_face_forms(self):
        data = copy(self.create_data)
        data['face_forms'] = [
            {
                "commitment_ref": "123",
                "start_date": "2025-07-11",
                "end_date": "2025-07-11",
                "dct_amt_usd": "100.00",
                "dct_amt_local": "11.00"
            },
            {
                "commitment_ref": "1234",
                "start_date": "2025-07-11",
                "end_date": "2025-09-11",
                "dct_amt_usd": "200.00",
                "dct_amt_local": "22.00"
            }
        ]
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        audit = Audit.objects.get(pk=response.data['id'])
        self.assertEqual(audit.face_forms.count(), response.data['face_forms'].__len__())
        self.assertEqual(audit.face_forms.first().commitment_ref, response.data['face_forms'][0]['commitment_ref'])
        self.assertEqual(audit.face_forms.first().dct_amt_usd.__str__(), response.data['face_forms'][0]['dct_amt_usd'])
        self.assertEqual(audit.face_forms.first().dct_amt_local.__str__(), response.data['face_forms'][0]['dct_amt_local'])
        self.assertEqual(audit.total_value, 300)
        self.assertEqual(audit.total_value_local, 33)
        self.assertEqual(audit.exchange_rate.__str__(), round(200 / 22, 2).__str__())
        self.assertEqual(audit.total_value, Decimal(response.data['total_value']))
        self.assertEqual(audit.total_value_local, Decimal(response.data['total_value_local']))


class TestSpotCheckCreateViewSet(TestEngagementCreateActivePDViewSet, BaseTestEngagementsCreateViewSet,
                                 BaseTenantTestCase):
    engagement_factory = SpotCheckFactory

    def test_list(self):
        self.endpoint = "spot-checks"
        section = SectionFactory()
        spot_check = SpotCheckFactory()
        spot_check.sections.set([section.pk])
        office = OfficeFactory()
        spot_check.offices.set([office.pk])
        response = response = self.forced_auth_req(
            'get',
            self.engagements_url(),
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found = False
        for data in response.data["results"]:
            if data["id"] == spot_check.pk:
                found = True
                self.assertEqual(
                    data["sections"],
                    [{"id": section.pk, "name": section.name}],
                )
                self.assertEqual(
                    data["offices"],
                    [{"id": office.pk, "name": office.name}],
                )
        self.assertTrue(found)

    def test_sections(self):
        self.endpoint = "spot-checks"
        section_1 = SectionFactory()
        section_2 = SectionFactory()
        self.create_data["sections"] = [section_1.pk, section_2.pk]
        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            sorted(response.data['sections'], key=lambda x: x["id"]),
            sorted(
                [
                    {"id": section_1.pk, "name": section_1.name},
                    {"id": section_2.pk, "name": section_2.name},
                ],
                key=lambda x: x["id"]
            ),
        )
        spot_check = SpotCheck.objects.get(pk=response.data["id"])
        self.assertEqual(
            sorted([s.pk for s in spot_check.sections.all()]),
            sorted([section_1.pk, section_2.pk]),
        )

    def test_offices(self):
        self.endpoint = "spot-checks"
        office_1 = OfficeFactory()
        office_2 = OfficeFactory()
        self.create_data["offices"] = [office_1.pk, office_2.pk]
        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            sorted(response.data['offices'], key=lambda x: x["id"]),
            sorted(
                [
                    {"id": office_1.pk, "name": office_1.name},
                    {"id": office_2.pk, "name": office_2.name},
                ],
                key=lambda x: x["id"],
            ),
        )
        spot_check = SpotCheck.objects.get(pk=response.data["id"])
        self.assertEqual(
            sorted([o.pk for o in spot_check.offices.all()]),
            sorted([office_1.pk, office_2.pk]),
        )

    def test_end_date_validation(self):
        data = copy(self.create_data)
        data['end_date'] = data['start_date'] - datetime.timedelta(days=1)
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)

    def test_face_form_validation(self):
        data = copy(self.create_data)
        data['face_forms'] = []
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You must specify at least one FACE Form.', response.data['non_field_errors'])

    def test_partner_contacted_at_validation(self):
        data = copy(self.create_data)
        data['partner_contacted_at'] = data['end_date'] - datetime.timedelta(days=1)
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('partner_contacted_at', response.data)


class TestSpecialAuditCreateViewSet(BaseTestEngagementsCreateViewSet, BaseTenantTestCase):
    engagement_factory = SpecialAuditFactory

    def setUp(self):
        super().setUp()
        self.create_data['specific_procedures'] = [
            {
                'description': sp.description,
                'finding': sp.finding,
            } for sp in self.engagement.specific_procedures.all()
        ]

    def test_engagement_with_active_pd(self):
        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_engagement_without_active_pd(self):
        del self.create_data['active_pd']

        response = self._do_create(self.unicef_focal_point, self.create_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_end_date_validation(self):
        data = copy(self.create_data)
        data['end_date'] = data['start_date'] - datetime.timedelta(days=1)
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)

    def test_partner_contacted_at_validation(self):
        data = copy(self.create_data)
        data['partner_contacted_at'] = data['end_date'] - datetime.timedelta(days=1)
        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('partner_contacted_at', response.data)

    def test_face_forms_with_total(self):
        data = copy(self.create_data)
        data['face_forms'] = [
            {
                "commitment_ref": "123",
                "start_date": "2025-07-11",
                "end_date": "2025-07-11",
                "dct_amt_usd": "321.00",
                "dct_amt_local": "222.00"
            }
        ]
        data['total_value'] = '333'
        data['total_value_local'] = '444'

        response = self._do_create(self.unicef_focal_point, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        sp_audit = SpecialAudit.objects.get(pk=response.data['id'])
        self.assertEqual(sp_audit.face_forms.count(), response.data['face_forms'].__len__())
        self.assertEqual(sp_audit.face_forms.first().commitment_ref, response.data['face_forms'][0]['commitment_ref'])
        self.assertEqual(sp_audit.face_forms.first().dct_amt_usd.__str__(), response.data['face_forms'][0]['dct_amt_usd'])
        self.assertEqual(sp_audit.face_forms.first().dct_amt_local.__str__(), response.data['face_forms'][0]['dct_amt_local'])
        self.assertEqual(sp_audit.total_value, 333)
        self.assertEqual(sp_audit.total_value_local, 444)
        self.assertEqual(sp_audit.exchange_rate.__str__(), round(333 / 444, 2).__str__())
        self.assertEqual(Decimal(data['total_value']), Decimal(response.data['total_value']))
        self.assertEqual(Decimal(data['total_value_local']), Decimal(response.data['total_value_local']))


class TestEngagementsUpdateViewSet(EngagementTransitionsTestCaseMixin, BaseTenantTestCase):
    engagement_factory = AuditFactory

    def _do_update(self, user, data):
        data = data or {}
        for date_field in [
            'start_date', 'end_date', 'partner_contacted_at',
            'date_of_field_visit', 'date_of_draft_report_to_ip',
            'date_of_comments_by_ip', 'date_of_draft_report_to_unicef',
            'date_of_comments_by_unicef'
        ]:
            if data.get(date_field):
                if isinstance(data[date_field], datetime.datetime):
                    data[date_field] = data[date_field].date()
                data[date_field] = data[date_field].isoformat()
        response = self.forced_auth_req(
            'patch',
            '/api/audit/audits/{}/'.format(self.engagement.id),
            user=user, data=data
        )
        return response

    def test_audited_expenditure_invalid(self):
        self.engagement.financial_findings_local = 2
        self.engagement.save(update_fields=['financial_findings_local'])
        response = self._do_update(self.auditor, {
            'audited_expenditure_local': 1,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data), 1)
        self.assertIn('audited_expenditure_local', response.data)

    def test_audited_expenditure_valid(self):
        self.engagement.financial_findings_local = 2
        self.engagement.save(update_fields=['financial_findings_local'])
        response = self._do_update(self.auditor, {
            'audited_expenditure_local': 10,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['audited_expenditure_local'], '10.00')

    def test_calculate_audited_expenditure(self):
        self.engagement.exchange_rate = 1.5
        self.engagement.save(update_fields=['exchange_rate'])
        response = self._do_update(self.auditor, {
            'audited_expenditure_local': 10,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['audited_expenditure'], '15.00')

    def test_date_of_field_visit_after_partner_contacted_at_validation(self):
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'date_of_field_visit': self.engagement.end_date,
            'date_of_draft_report_to_ip': None,
            'date_of_comments_by_ip': None,
            'date_of_draft_report_to_unicef': None,
            'date_of_comments_by_unicef': None,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_field_visit', response.data)

    def test_date_of_draft_report_to_ip_after_date_of_field_visit_validation(self):
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'date_of_field_visit': self.engagement.end_date + datetime.timedelta(days=2),
            'date_of_draft_report_to_ip': self.engagement.end_date,
            'date_of_comments_by_ip': None,
            'date_of_draft_report_to_unicef': None,
            'date_of_comments_by_unicef': None,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_field_visit', response.data)

    def test_date_of_comments_by_ip_after_date_of_draft_report_to_ip_validation(self):
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'date_of_field_visit': self.engagement.end_date + datetime.timedelta(days=2),
            'date_of_draft_report_to_ip': self.engagement.end_date + datetime.timedelta(days=3),
            'date_of_comments_by_ip': self.engagement.end_date,
            'date_of_draft_report_to_unicef': None,
            'date_of_comments_by_unicef': None,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_comments_by_ip', response.data)

    def test_date_of_draft_report_to_unicef_after_date_of_comments_by_ip_validation(self):
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'date_of_field_visit': self.engagement.end_date + datetime.timedelta(days=2),
            'date_of_draft_report_to_ip': self.engagement.end_date + datetime.timedelta(days=3),
            'date_of_comments_by_ip': self.engagement.end_date + datetime.timedelta(days=4),
            'date_of_draft_report_to_unicef': self.engagement.end_date,
            'date_of_comments_by_unicef': None,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_draft_report_to_unicef', response.data)

    def test_date_of_comments_by_unicef_after_date_of_draft_report_to_unicef_validation(self):
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'date_of_field_visit': self.engagement.end_date + datetime.timedelta(days=2),
            'date_of_draft_report_to_ip': self.engagement.end_date + datetime.timedelta(days=3),
            'date_of_comments_by_ip': self.engagement.end_date + datetime.timedelta(days=4),
            'date_of_draft_report_to_unicef': self.engagement.end_date + datetime.timedelta(days=5),
            'date_of_comments_by_unicef': self.engagement.end_date,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_comments_by_unicef', response.data)

    def test_date_of_final_report_after_skip_date_ip_contacted_at_validation(self):
        self.engagement.date_of_final_report = settings.FAM_SKIP_IP_CONTACTED_VALIDATION_DATE + datetime.timedelta(days=1)
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=-1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'amount_refunded': 123,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('partner_contacted_at', response.data)

    def test_date_of_final_report_before_skip_date_ip_contacted_at_validation(self):
        self.engagement.date_of_final_report = settings.FAM_SKIP_IP_CONTACTED_VALIDATION_DATE + datetime.timedelta(days=-1)
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=-1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'amount_refunded': 123,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('partner_contacted_at', response.data)

    def test_dates_update_ok(self):
        self.engagement.partner_contacted_at = self.engagement.end_date + datetime.timedelta(days=1)
        self.engagement.save()
        response = self._do_update(self.auditor, {
            'date_of_field_visit': self.engagement.end_date + datetime.timedelta(days=2),
            'date_of_draft_report_to_ip': self.engagement.end_date + datetime.timedelta(days=3),
            'date_of_comments_by_ip': self.engagement.end_date + datetime.timedelta(days=4),
            'date_of_draft_report_to_unicef': self.engagement.end_date + datetime.timedelta(days=5),
            'date_of_comments_by_unicef': self.engagement.end_date + datetime.timedelta(days=6),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_members_update(self):
        self.assertEqual(self.engagement.staff_members.count(), 2)
        new_auditor = AuditorUserFactory(partner_firm=self.auditor_firm)

        staff_list = list(self.engagement.staff_members.values_list('id', flat=True))
        staff_list.append(new_auditor.pk)
        response = self._do_update(self.auditor, {
            'staff_members': staff_list
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.engagement.staff_members.count(), 3)

        new_auditor.realms.all().update(is_active=False)
        response = self._do_update(self.auditor, {
            'staff_members': staff_list
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_financial_finding_set(self):
        self.assertEqual(self.engagement.financial_finding_set.count(), 0)
        self.assertEqual(self.engagement.financial_findings, 0)
        self.assertEqual(self.engagement.financial_findings_local, 0)
        response = self._do_update(self.auditor, {"financial_finding_set": [
            {
                "title": "vat-incorrectly-claimed",
                "local_amount": "96533.00",
                "amount": "1253.67",
                "description": "During the audit process..",
                "recommendation": "We recommend proper control procedures",
                "ip_comments": "payments accordingly"
            }
        ]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.engagement.refresh_from_db()
        self.assertEqual(self.engagement.financial_findings, Decimal('1253.67'))
        self.assertEqual(self.engagement.financial_findings_local, Decimal('96533.00'))
        self.assertEqual(response.data['financial_findings'], '1253.67')
        self.assertEqual(response.data['financial_findings_local'], '96533.00')


class TestEngagementActionPointViewSet(EngagementTransitionsTestCaseMixin, BaseTenantTestCase):
    engagement_factory = MicroAssessmentFactory

    def test_action_point_added_focal_point(self):
        self._init_finalized_engagement()
        self.assertEqual(self.engagement.action_points.count(), 0)

        response = self.forced_auth_req(
            'post',
            '/api/audit/engagements/{}/action-points/'.format(self.engagement.id),
            user=self.unicef_focal_point,
            data={
                'category': ActionPointCategoryFactory(module='audit').id,
                'description': fuzzy.FuzzyText(length=100).fuzz(),
                'due_date': fuzzy.FuzzyDate(datetime.date(2001, 1, 1)).fuzz(),
                'assigned_to': self.unicef_user.id,
                'section': SectionFactory().id,
                'office': self.unicef_focal_point.profile.tenant_profile.office.id,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.engagement.action_points.count(), 1)
        self.assertIsNotNone(self.engagement.action_points.first().partner)

    def test_action_point_added_unicef_user(self):
        self._init_finalized_engagement()
        self.assertEqual(self.engagement.action_points.count(), 0)

        response = self.forced_auth_req(
            'post',
            '/api/audit/engagements/{}/action-points/'.format(self.engagement.id),
            user=self.unicef_user,
            data={
                'category': ActionPointCategoryFactory(module='audit').id,
                'description': fuzzy.FuzzyText(length=100).fuzz(),
                'due_date': fuzzy.FuzzyDate(datetime.date(2001, 1, 1)).fuzz(),
                'assigned_to': self.unicef_user.id,
                'section': SectionFactory().id,
                'office': self.unicef_focal_point.profile.tenant_profile.office.id,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.engagement.action_points.count(), 1)
        self.assertIsNotNone(self.engagement.action_points.first().partner)

    def _test_action_point_editable(self, action_point, user, editable=True):
        response = self.forced_auth_req(
            'options',
            '/api/audit/engagements/{}/action-points/{}/'.format(self.engagement.id, action_point.id),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if editable:
            self.assertIn('PUT', response.data['actions'].keys())
            self.assertListEqual(
                sorted([
                    'category', 'assigned_to', 'high_priority', 'due_date', 'description',
                    'section', 'office', 'intervention'
                ]),
                sorted(list(response.data['actions']['PUT'].keys()))
            )
        else:
            self.assertNotIn('PUT', response.data['actions'].keys())

    def test_action_point_editable_by_author(self):
        self._init_finalized_engagement()
        action_point = ActionPointFactory(engagement=self.engagement, status='pre_completed')

        self._test_action_point_editable(action_point, action_point.author)

    def test_action_point_editable_by_focal_point(self):
        self._init_finalized_engagement()
        action_point = ActionPointFactory(engagement=self.engagement, status='pre_completed')

        self._test_action_point_editable(action_point, self.unicef_focal_point)

    def test_action_point_readonly_by_simple_unicef_user(self):
        self._init_finalized_engagement()
        action_point = ActionPointFactory(engagement=self.engagement, status='pre_completed')

        self._test_action_point_editable(action_point, self.unicef_user, editable=False)

    def test_action_point_readonly_by_author_on_complete(self):
        self._init_finalized_engagement()
        action_point = ActionPointFactory(engagement=self.engagement, status='completed')

        self._test_action_point_editable(action_point, action_point.author, editable=False)

    def test_action_point_readonly_by_focal_point_on_complete(self):
        self._init_finalized_engagement()
        action_point = ActionPointFactory(engagement=self.engagement, status='completed')

        self._test_action_point_editable(action_point, self.unicef_focal_point, editable=False)


class TestSpotCheckDetail(SCTransitionsTestCaseMixin, BaseTenantTestCase):
    engagement_factory = SpotCheckFactory

    def test_detail_pending_unsupported_amount(self):
        self._fill_sc_specified_fields()

        self.engagement.amount_refunded = 100
        self.engagement.additional_supporting_documentation_provided = 25
        self.engagement.justification_provided_and_accepted = 75
        self.engagement.writeoff = 50
        self.engagement.save()
        self._init_finalized_engagement()

        self.engagement.total_amount_tested_local = 1000
        self.engagement.total_amount_of_ineligible_expenditure_local = 300
        self.engagement.exchange_rate = 2
        self.engagement.save()

        response = self.forced_auth_req(
            'get',
            reverse('audit:spot-checks-detail', args=[self.engagement.pk]),
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_amount = (
            self.engagement.total_amount_of_ineligible_expenditure - self.engagement.additional_supporting_documentation_provided -
            self.engagement.justification_provided_and_accepted - self.engagement.write_off_required - self.engagement.amount_refunded
        )
        self.assertEqual("{:.2f}".format(expected_amount), response.data['pending_unsupported_amount'])
        self.assertEqual(expected_amount, self.engagement.pending_unsupported_amount)
        self.assertEqual(float(response.data['total_amount_tested']), 2000.00)
        self.assertEqual(float(response.data['total_amount_of_ineligible_expenditure']), 600.00)


class TestStaffSpotCheck(AuditTestCaseMixin, BaseTenantTestCase):
    fixtures = ('audit_staff_organization',)

    def test_list_options(self):
        response = self.forced_auth_req(
            'options',
            reverse('audit:staff-spot-checks-list'),
            user=self.unicef_focal_point
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('POST', response.data['actions'])

    def test_create(self):
        spot_check = SpotCheckFactory()
        create_data = {
            'end_date': spot_check.end_date,
            'start_date': spot_check.start_date,
            'partner_contacted_at': spot_check.partner_contacted_at,
            'total_value': spot_check.total_value,
            'partner': spot_check.partner_id,
            'authorized_officers': spot_check.authorized_officers.values_list('id', flat=True),
            'users_notified': spot_check.users_notified.values_list('id', flat=True),
            'staff_members': spot_check.staff_members.values_list('id', flat=True),
            'active_pd': spot_check.active_pd.values_list('id', flat=True),
            'shared_ip_with': spot_check.shared_ip_with,
        }

        response = self.forced_auth_req(
            'post',
            reverse('audit:staff-spot-checks-list'),
            user=self.unicef_focal_point,
            data=create_data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['agreement'])

    def test_detail_staff_members(self):
        active_staff_list = []
        for i in range(3):
            active_staff_list.append(AuditFocalPointUserFactory())

        inactive_unicef_focal_point = AuditFocalPointUserFactory()
        inactive_unicef_focal_point.realms.update(is_active=False)

        spot_check = SpotCheckFactory(staff_members=active_staff_list + [inactive_unicef_focal_point])

        response = self.forced_auth_req(
            'get',
            reverse('audit:staff-spot-checks-detail', args=[spot_check.pk]),
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['staff_members']), spot_check.staff_members.count())
        self.assertEqual(
            [inactive_unicef_focal_point.pk],
            [staff['id'] for staff in response.data['staff_members'] if not staff['has_active_realm']]
        )
        self.assertEqual(
            sorted([staff.pk for staff in active_staff_list]),
            sorted([staff['id'] for staff in response.data['staff_members'] if staff['has_active_realm']])
        )

    def test_list(self):
        SpotCheckFactory()
        staff_spot_check = StaffSpotCheckFactory()

        response = self.forced_auth_req(
            'get',
            reverse('audit:staff-spot-checks-list'),
            user=self.unicef_focal_point
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], staff_spot_check.id)

        attachments_response = self.forced_auth_req(
            'get',
            reverse('audit:engagement-attachments-list', args=[staff_spot_check.id]),
            user=self.unicef_focal_point,
        )
        self.assertEqual(attachments_response.status_code, status.HTTP_200_OK)

    def test_engagements_list(self):
        spot_check = SpotCheckFactory()
        StaffSpotCheckFactory()

        response = self.forced_auth_req(
            'get',
            reverse('audit:engagements-list'),
            user=self.unicef_focal_point
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], spot_check.id)

        attachments_response = self.forced_auth_req(
            'get',
            reverse('audit:engagement-attachments-list', args=[spot_check.id]),
            user=self.unicef_focal_point,
        )
        self.assertEqual(attachments_response.status_code, status.HTTP_200_OK)


class TestMetadataDetailViewSet(EngagementTransitionsTestCaseMixin):
    def _test_risk_choices(self, field, expected_choices):
        response = self.forced_auth_req(
            'options',
            '/api/audit/{}/{}/'.format(self.endpoint, self.engagement.id),
            user=self.auditor
        )
        self.assertIn('GET', response.data['actions'])
        get = response.data['actions']['GET']

        self.assertIn(field, get)
        self.assertIn('blueprints', get[field]['children'])

        blueprint_data = get[field]['children']['blueprints']['child']['children']
        if 'risk' in blueprint_data:
            risk_fields = blueprint_data['risk']['children']
        elif 'risks' in blueprint_data:
            risk_fields = blueprint_data['risks']['child']['children']
        else:
            self.fail('risk choices not found')

        self.assertIn('choices', risk_fields['value'])
        self.assertListEqual(
            [{'value': c, 'display_name': str(v)} for c, v in expected_choices],
            risk_fields['value']['choices']
        )

    def _test_send_back_comment(self):
        response = self.forced_auth_req(
            'options',
            '/api/audit/{}/{}/'.format(self.endpoint, self.engagement.id),
            user=self.auditor
        )
        self.assertIn('GET', response.data['actions'])
        get = response.data['actions']['GET']
        self.assertIn('send_back_comment', get)


class TestEngagementMetadataViewSet(AuditTestCaseMixin, BaseTenantTestCase):
    endpoint = "engagements"

    def test_staff_members(self):
        response = self.forced_auth_req(
            'options',
            '/api/audit/{}/'.format(self.endpoint),
            user=self.unicef_focal_point
        )
        self.assertIn('POST', response.data['actions'])
        self.assertIn('staff_members', response.data['actions']['POST'])


class TestMicroAssessmentMetadataDetailViewSet(TestMetadataDetailViewSet, BaseTenantTestCase):
    engagement_factory = MicroAssessmentFactory
    endpoint = 'micro-assessments'

    def test_overall_choices(self):
        self._test_risk_choices('overall_risk_assessment', Risk.POSITIVE_VALUES)

    def test_subject_areas_choices(self):
        self._test_risk_choices('test_subject_areas', Risk.VALUES)

    def test_send_back_comment_ip_contacted(self):
        self.assertEqual(self.engagement.status, Engagement.PARTNER_CONTACTED)
        self._test_send_back_comment()

    def test_send_back_comment_submitted(self):
        self._init_submitted_engagement()
        self.assertEqual(self.engagement.status, Engagement.REPORT_SUBMITTED)
        self._test_send_back_comment()


class TestAuditMetadataDetailViewSet(TestMetadataDetailViewSet, BaseTenantTestCase):
    engagement_factory = AuditFactory
    endpoint = 'audits'

    def test_weaknesses_choices(self):
        self._test_risk_choices('key_internal_weakness', Risk.AUDIT_VALUES)


class TestSpotCheckMetadataDetailViewSet(TestMetadataDetailViewSet, BaseTenantTestCase):
    engagement_factory = StaffSpotCheckFactory
    endpoint = 'spot-checks'

    def test_users_notified_auditor_not_unicef(self):
        self.assertFalse(self.auditor.is_unicef_user())
        spot_check = self.engagement_factory(
            staff_members=[self.auditor], agreement__auditor_firm=self.auditor_firm
        )
        response = self.forced_auth_req(
            'options',
            '/api/audit/{}/{}/'.format(self.endpoint, spot_check.id),
            user=self.auditor
        )
        self.assertIn('GET', response.data['actions'])
        get = response.data['actions']['GET']
        self.assertIn('users_notified', get)
        put = response.data['actions']['PUT']
        self.assertNotIn('users_notified', put)

    def test_users_notified_auditor_is_unicef(self):
        spot_check = self.engagement_factory(
            staff_members=[self.unicef_focal_point], agreement__auditor_firm=self.auditor_firm
        )
        self.assertTrue(self.unicef_focal_point.is_unicef_user())
        response = self.forced_auth_req(
            'options',
            '/api/audit/{}/{}/'.format(self.endpoint, spot_check.id),
            user=self.unicef_focal_point
        )
        self.assertIn('GET', response.data['actions'])
        get = response.data['actions']['GET']
        self.assertIn('users_notified', get)
        put = response.data['actions']['PUT']
        self.assertIn('users_notified', put)


class TestAuditorFirmViewSet(AuditTestCaseMixin, BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.second_auditor_firm = AuditPartnerFactory()
        self.engagement = EngagementFactory(agreement__auditor_firm=self.auditor_firm)

    def _test_list_view(self, user, expected_firms=None, expected_status=status.HTTP_200_OK):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/',
            user=user
        )

        self.assertEqual(response.status_code, expected_status)
        if expected_status == status.HTTP_200_OK:
            self.assertCountEqual(
                map(lambda x: x['id'], response.data['results']),
                map(lambda x: x.id, expected_firms)
            )

    def test_focal_point_list_view(self):
        self._test_list_view(self.unicef_focal_point, [self.auditor_firm, self.second_auditor_firm])

    def test_unicef_list_view(self):
        self._test_list_view(self.unicef_user, [self.auditor_firm, self.second_auditor_firm])

    def test_auditor_list_view(self):
        self._test_list_view(self.auditor, [self.auditor_firm])

    def test_inactive_auditor_list_view(self):
        # the user belongs to two organizations; just one of them is active
        second_auditor = UserFactory(realms__data=[])
        second_auditor.profile.organization = self.second_auditor_firm.organization
        second_auditor.profile.save()
        RealmFactory(
            user=second_auditor,
            country=connection.tenant,
            organization=self.auditor_firm.organization,
            group=Auditor.as_group(),
        )
        RealmFactory(
            user=second_auditor,
            country=connection.tenant,
            organization=self.second_auditor_firm.organization,
            group=Auditor.as_group(),
        )
        self._test_list_view(second_auditor, [self.second_auditor_firm])

    def test_usual_user_list_view(self):
        self._test_list_view(self.usual_user, expected_status=status.HTTP_403_FORBIDDEN)

    def test_unicef_search_view(self):
        UserFactory()
        user = UserFactory(email='test@example.com')
        self.engagement.staff_members.add(user)

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/users/',
            user=self.unicef_user,
            data={'search': user.email}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIsNone(response.data[0]['auditor_firm'])

    def test_users_list_queries(self):
        for _i in range(10):
            user = UserFactory()
            self.engagement.staff_members.add(user)

        with self.assertNumQueries(2):
            response = self.forced_auth_req(
                'get',
                '/api/audit/audit-firms/users/',
                user=self.unicef_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('auditor_firm', response.data[0])

    def test_users_list_queries_verbosity_minimal(self):
        for _i in range(10):
            user = UserFactory()
            self.engagement.staff_members.add(user)

        with self.assertNumQueries(2):
            response = self.forced_auth_req(
                'get',
                '/api/audit/audit-firms/users/',
                user=self.unicef_user,
                data={'verbosity': 'minimal'}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('auditor_firm', response.data[0])


class TestAuditorStaffMembersViewSet(AuditTestCaseMixin, BaseTenantTestCase):
    def test_list_view(self):
        inactive_auditor = AuditorUserFactory(is_active=False, partner_firm=self.auditor_firm)
        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{0}/staff-members/'.format(self.auditor_firm.id),
            user=self.unicef_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertTrue(inactive_auditor.pk in map(lambda x: x['id'], response.data['results']))

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{0}/staff-members/'.format(self.auditor_firm.id),
            user=self.usual_user
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_global_search(self):
        UserFactory()
        user = UserFactory()
        EngagementFactory(staff_members=[user])

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/users/',
            data={'email': user.email},
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], user.email)

    def test_staff_search(self):
        AuditorUserFactory(partner_firm=self.auditor_firm)
        user = AuditorUserFactory(partner_firm=self.auditor_firm, email='test_unique@example.com')

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{}/staff-members/'.format(self.auditor_firm.id),
            data={'search': 'test_unique'},
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['user']['email'], user.email)

    def test_countries_filter(self):
        AuditorUserFactory(partner_firm=self.auditor_firm)
        user = AuditorUserFactory(partner_firm=self.auditor_firm)
        another_country = CountryFactory(name=fuzzy.FuzzyText(length=20))
        RealmFactory(
            user=user,
            country=another_country,
            organization=self.auditor_firm.organization,
            group=Auditor.as_group()
        )

        response = self.forced_auth_req(
            'get',
            '/api/audit/audit-firms/{}/staff-members/'.format(self.auditor_firm.id),
            data={'user__profile__countries_available__name': 'QQQQQQQQQQQQQQQQ'},
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # since we cannot create country to test it properly, just check filter excludes everything from response
        self.assertEqual(response.data['count'], 0)

    def test_detail_view(self):
        # todo: get rid of staff_members
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
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestEngagementSpecialPDFExportViewSet(EngagementTransitionsTestCaseMixin, BaseTenantTestCase):
    engagement_factory = SpecialAuditFactory

    def _test_pdf_view(self, user, status_code=status.HTTP_200_OK):
        response = self.forced_auth_req(
            'get',
            '/api/audit/special-audits/{}/pdf/'.format(self.engagement.id),
            user=user
        )

        self.assertEqual(response.status_code, status_code)
        if status_code == status.HTTP_200_OK:
            self.assertIn('Content-Disposition', response.headers)

    def test_guest(self):
        self.user = None
        self._test_pdf_view(None, status.HTTP_403_FORBIDDEN)

    def test_common_user(self):
        self._test_pdf_view(self.usual_user, status.HTTP_404_NOT_FOUND)

    def test_unicef_user(self):
        self._test_pdf_view(self.unicef_user)

    def test_auditor(self):
        self._test_pdf_view(self.auditor)

    def test_auditor_with_attachment(self):
        file_type = AttachmentFileTypeFactory(
            code="audit_report"
        )
        AttachmentFactory(
            file="test_report.pdf",
            file_type=file_type,
            code=file_type.code,
            content_object=self.engagement
        )
        self._test_pdf_view(self.auditor)

    def test_focal_point(self):
        self._test_pdf_view(self.unicef_focal_point)


class TestEngagementPDFExportViewSet(EngagementTransitionsTestCaseMixin, BaseTenantTestCase):
    engagement_factory = AuditFactory

    def _test_pdf_view(self, user, status_code=status.HTTP_200_OK):
        response = self.forced_auth_req(
            'get',
            '/api/audit/audits/{}/pdf/'.format(self.engagement.id),
            user=user
        )

        self.assertEqual(response.status_code, status_code)
        if status_code == status.HTTP_200_OK:
            self.assertIn('Content-Disposition', response.headers)

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


class TestEngagementCSVExportViewSet(EngagementTransitionsTestCaseMixin, BaseTenantTestCase):
    engagement_factory = MicroAssessmentFactory

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('tenant_loaddata', 'audit_risks_blueprints', verbosity=0)

    def test_csv_view(self):
        response = self.forced_auth_req(
            'get',
            '/api/audit/micro-assessments/{}/csv/'.format(self.engagement.id),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])


class TestPurchaseOrderView(AuditTestCaseMixin, BaseTenantTestCase):
    def test_get_not_found(self):
        """If instance does not exist, code will attempt to sync,
        and if still does not exist then return 404
        """
        mock_sync = Mock()
        with patch("etools.applications.audit.views.POSynchronizer", mock_sync):
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


class TestEngagementPartnerView(AuditTestCaseMixin, BaseTenantTestCase):
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


class TestEngagementAttachmentsView(MATransitionsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.file_type = AttachmentFileTypeFactory(group=['audit_engagement'])

    def test_list(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.engagement.engagement_attachments.add(attachment)
        attachments_num = self.engagement.engagement_attachments.count()
        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:engagement-attachments-list',
                args=[self.engagement.pk],
            ),
            user=self.unicef_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), attachments_num)

    def test_get(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.engagement.engagement_attachments.add(attachment)

        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_does_not_belong(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.engagement.engagement_attachments.add(attachment)

        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:engagement-attachments-detail',
                args=[EngagementFactory().pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_non_existent(self):
        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, 111111],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post(self):
        attachment = AttachmentFactory(file="sample.pdf")
        self.assertIsNone(attachment.object_id)
        self.assertNotEqual(attachment.code, "audit_engagement")

        response = self.forced_auth_req(
            'post',
            reverse(
                'audit:engagement-attachments-list',
                args=[self.engagement.pk],
            ),
            user=self.unicef_focal_point,
            data={
                'file_type': self.file_type.pk,
                'attachment': attachment.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attachment.refresh_from_db()
        self.assertEqual(attachment.object_id, self.engagement.pk)
        self.assertEqual(attachment.code, "audit_engagement")

    def test_patch(self):
        file_type_old = AttachmentFileTypeFactory(
            group=["different_engagement"],
        )
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=file_type_old,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.engagement.engagement_attachments.add(attachment)
        self.assertNotEqual(attachment.file_type, self.file_type)

        response = self.forced_auth_req(
            'patch',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.unicef_focal_point,
            data={
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment.refresh_from_db()
        self.assertEqual(attachment.file_type, self.file_type)

    def test_patch_non_existent(self):
        file_type_old = AttachmentFileTypeFactory(
            group=["different_engagement"],
        )
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=file_type_old,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.assertNotEqual(attachment.file_type, self.file_type)

        response = self.forced_auth_req(
            'patch',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, 111111],
            ),
            user=self.unicef_focal_point,
            data={
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_does_not_belong(self):
        file_type_old = AttachmentFileTypeFactory(
            group=["different_engagement"],
        )
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=file_type_old,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.engagement.engagement_attachments.add(attachment)
        self.assertNotEqual(attachment.file_type, self.file_type)

        response = self.forced_auth_req(
            'patch',
            reverse(
                'audit:engagement-attachments-detail',
                args=[EngagementFactory().pk, attachment.pk]
            ),
            user=self.unicef_focal_point,
            data={
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.engagement.engagement_attachments.add(attachment)
        attachment_qs = self.engagement.engagement_attachments
        attachments_num = attachment_qs.count()

        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(attachment_qs.count(), attachments_num - 1)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_delete_non_existent(self):
        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, 11111111],
            ),
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_does_not_belong(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_engagement",
        )
        self.engagement.engagement_attachments.add(attachment)

        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:engagement-attachments-detail',
                args=[EngagementFactory().pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_meta_focal_point(self):
        response = self.forced_auth_req(
            'options',
            reverse('audit:engagement-attachments-list', args=['new']),
            user=self.unicef_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('POST', response.data['actions'])
        self.assertIn('GET', response.data['actions'])

    def test_create_meta_unicef_user(self):
        response = self.forced_auth_req(
            'options',
            reverse('audit:engagement-attachments-list', args=['new']),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('POST', response.data['actions'])
        self.assertIn('GET', response.data['actions'])


class TestEngagementReportAttachmentsView(MATransitionsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.file_type = AttachmentFileTypeFactory(group=['audit_report'])

    def test_list(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.engagement.report_attachments.add(attachment)
        attachments_num = self.engagement.report_attachments.count()

        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:report-attachments-list',
                args=[self.engagement.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), attachments_num)

    def test_get(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.engagement.report_attachments.add(attachment)

        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:report-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], attachment.pk)

    def test_get_does_not_belong(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.engagement.report_attachments.add(attachment)

        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:report-attachments-detail',
                args=[EngagementFactory().pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:report-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], attachment.pk)

    def test_get_non_existent(self):
        response = self.forced_auth_req(
            'get',
            reverse(
                'audit:report-attachments-detail',
                args=[self.engagement.pk, 1111111111],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post(self):
        attachment = AttachmentFactory(file="sample.pdf")
        self.assertIsNone(attachment.object_id)
        self.assertNotEqual(attachment.code, "audit_report")

        response = self.forced_auth_req(
            'post',
            reverse(
                'audit:report-attachments-list',
                args=[self.engagement.pk],
            ),
            user=self.unicef_focal_point,
            data={
                'file_type': self.file_type.pk,
                'attachment': attachment.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attachment.refresh_from_db()
        self.assertEqual(attachment.object_id, self.engagement.pk)
        self.assertEqual(attachment.code, "audit_report")

    def test_patch(self):
        file_type_old = AttachmentFileTypeFactory(group=["different_report"])
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=file_type_old,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.assertNotEqual(attachment.file_type, self.file_type)
        self.engagement.report_attachments.add(attachment)

        response = self.forced_auth_req(
            'patch',
            reverse(
                'audit:report-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.unicef_focal_point,
            data={
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment.refresh_from_db()
        self.assertEqual(attachment.file_type, self.file_type)

    def test_patch_non_existent(self):
        file_type_old = AttachmentFileTypeFactory(
            group=["different_engagement"],
        )
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=file_type_old,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.assertNotEqual(attachment.file_type, self.file_type)

        response = self.forced_auth_req(
            'patch',
            reverse(
                'audit:engagement-attachments-detail',
                args=[self.engagement.pk, 111111],
            ),
            user=self.unicef_focal_point,
            data={
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_does_not_belong(self):
        file_type_old = AttachmentFileTypeFactory(
            group=["different_engagement"],
        )
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=file_type_old,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.engagement.engagement_attachments.add(attachment)
        self.assertNotEqual(attachment.file_type, self.file_type)

        response = self.forced_auth_req(
            'patch',
            reverse(
                'audit:engagement-attachments-detail',
                args=[EngagementFactory().pk, attachment.pk]
            ),
            user=self.unicef_focal_point,
            data={
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.engagement.engagement_attachments.add(attachment)
        attachment_qs = self.engagement.report_attachments
        attachments_num = attachment_qs.count()

        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:report-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(attachment_qs.count(), attachments_num - 1)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_delete_non_existent(self):
        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:report-attachments-detail',
                args=[self.engagement.pk, 1111],
            ),
            user=self.unicef_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_does_not_belong(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Engagement),
            object_id=self.engagement.pk,
            code="audit_report",
        )
        self.engagement.report_attachments.add(attachment)

        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:report-attachments-detail',
                args=[EngagementFactory().pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.forced_auth_req(
            'delete',
            reverse(
                'audit:report-attachments-detail',
                args=[self.engagement.pk, attachment.pk],
            ),
            user=self.auditor
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
