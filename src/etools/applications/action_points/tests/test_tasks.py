import datetime
from unittest.mock import Mock, patch

from django.core.management import call_command

from etools.applications.action_points import tasks
from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.core.tests.cases import BaseTenantTestCase

EMAIL_PATH = "etools.applications.action_points.tasks.send_notification_with_template"


class TestNotifyActionPointOverdue(BaseTenantTestCase):
    def setUp(self):
        call_command('update_notifications')
        self.mock_email = Mock()
        self.yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.overdue_qs = ActionPoint.objects.exclude(
            status=ActionPoint.STATUS_COMPLETED
        ).filter(due_date=self.yesterday)

    def test_overdue_none(self):
        self.assertFalse(self.overdue_qs.count())
        with patch(EMAIL_PATH, self.mock_email):
            tasks.notify_overdue_action_points()
        self.assertEqual(self.mock_email.call_count, 0)

    def test_overdue(self):
        ActionPointFactory(due_date=self.yesterday)
        self.assertTrue(self.overdue_qs.count())
        with patch(EMAIL_PATH, self.mock_email):
            tasks.notify_overdue_action_points()
        self.assertEqual(self.mock_email.call_count, self.overdue_qs.count())
