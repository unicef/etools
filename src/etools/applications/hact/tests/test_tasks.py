from unittest.mock import Mock, patch

from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.hact.models import AggregateHact
from etools.applications.hact.tasks import (
    notify_hact_update,
    update_aggregate_hact_values,
    update_hact_for_country,
    update_hact_values,
)
from etools.applications.hact.tests.factories import AggregateHactFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.permissions import UNICEF_USER
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.models import Country
from etools.applications.users.tests.factories import UserFactory
from etools.applications.vision.models import VisionSyncLog
from etools.libraries.djangolib.models import GroupWrapper


class TestAggregateHactValues(BaseTenantTestCase):
    """
    Test task which freeze global aggregated values for hact dashboard
    """

    def test_task_create(self):
        self.assertEqual(AggregateHact.objects.count(), 0)
        update_aggregate_hact_values()
        self.assertEqual(AggregateHact.objects.count(), 1)

    def test_task_update(self):
        AggregateHactFactory()
        self.assertEqual(AggregateHact.objects.count(), 1)
        update_aggregate_hact_values()
        self.assertEqual(AggregateHact.objects.count(), 1)


class TestHactForCountry(BaseTenantTestCase):

    def test_task_create(self):
        logs = VisionSyncLog.objects.all()
        self.assertEqual(logs.count(), 0)
        PartnerFactory(organization=OrganizationFactory(name="Partner XYZ"), reported_cy=20000)
        update_hact_for_country(self.tenant.business_area_code)
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.total_records, 1)
        self.assertEqual(log.total_processed, 1)
        self.assertTrue(log.successful)

    def test_task_update(self):
        logs = VisionSyncLog.objects.all()
        self.assertEqual(logs.count(), 0)
        partner = PartnerFactory(organization=OrganizationFactory(name="Partner XYZ"), reported_cy=20000)
        unicef_focal_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, UNICEFAuditFocalPoint.name]
        )
        update_hact_for_country(self.tenant.business_area_code)
        self.assertEqual(logs.count(), 1)

        partner.hact_values = {
            "outstanding_findings": 0,
            "audits": {
                "completed": 0,
                "minimum_requirements": 1
            },
            "programmatic_visits": {
                "completed": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "planned": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "minimum_requirements": 2
            },
            "spot_checks": {
                "completed": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "planned": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "follow_up_required": 0,
                "minimum_requirements": 3
            }
        }
        partner.save(update_fields=['hact_values'])

        mock_send = Mock()
        with patch("etools.applications.hact.tasks.send_notification_with_template", mock_send):
            update_hact_for_country(self.tenant.business_area_code)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args.kwargs['recipients'], [unicef_focal_user.email])

        log = logs.first()
        self.assertEqual(log.total_records, 1)
        self.assertEqual(log.total_processed, 1)
        self.assertTrue(log.successful)


class TestUpdateHactValues(BaseTenantTestCase):

    def test_update_hact_values(self):
        mock_send = Mock()
        with patch("etools.applications.hact.tasks.update_hact_for_country.delay", mock_send):
            update_hact_values()
        self.assertEqual(mock_send.call_count, 1)


class TestNotifyHactUpdate(BaseTenantTestCase):

    def test_notify_hact_update(self):
        # clearing groups cache
        GroupWrapper.invalidate_instances()

        logs = VisionSyncLog.objects.all()
        self.assertEqual(logs.count(), 0)
        partner = PartnerFactory(organization=OrganizationFactory(name="Partner XYZ"), reported_cy=20000)

        active_unicef_focal_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, UNICEFAuditFocalPoint.name]
        )
        active_unicef_focal_user.realms.update(is_active=True)

        active_unicef_focal_user2 = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, UNICEFAuditFocalPoint.name]
        )
        active_unicef_focal_user2.realms.update(is_active=True)

        inactive_unicef_focal_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, UNICEFAuditFocalPoint.name]
        )
        inactive_unicef_focal_user.realms.update(is_active=False)

        update_hact_for_country(self.tenant.business_area_code)
        self.assertEqual(logs.count(), 1)

        partner.hact_values = {
            "outstanding_findings": 0,
            "audits": {
                "completed": 0,
                "minimum_requirements": 1
            },
            "programmatic_visits": {
                "completed": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "planned": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "minimum_requirements": 2
            },
            "spot_checks": {
                "completed": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "planned": {
                    "q1": 0,
                    "total": 0,
                    "q3": 0,
                    "q2": 0,
                    "q4": 0
                },
                "follow_up_required": 0,
                "minimum_requirements": 3
            }
        }
        partner.save(update_fields=['hact_values'])

        mock_send = Mock()
        with patch("etools.applications.hact.tasks.send_notification_with_template", mock_send):
            notify_hact_update(["Partner XYZ"], Country.objects.get(business_area_code=self.tenant.business_area_code).id)
        self.assertEqual(mock_send.call_count, 1)

        expected_recipients = list([active_unicef_focal_user2.email, active_unicef_focal_user.email])

        actual_call_args = mock_send.call_args.kwargs['recipients']
        assert set(actual_call_args) == set(expected_recipients), \
            f"Expected {expected_recipients}, got {actual_call_args}"
