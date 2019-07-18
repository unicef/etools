from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMPartnerStaffMemberFactory


class TestMonitoringActivityValidations(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(fm_user=True)

    def test_tpm_partner_for_staff_activity(self):
        activity = MonitoringActivityFactory(activity_type='staff', tpm_partner=TPMPartnerFactory())
        self.assertTrue(ActivityValid(activity, user=self.user).errors)

    def test_tpm_partner_for_tpm_activity(self):
        activity = MonitoringActivityFactory(activity_type='tpm', tpm_partner=TPMPartnerFactory())
        self.assertFalse(ActivityValid(activity, user=self.user).errors)

    def test_empty_partner_for_tpm_activity(self):
        activity = MonitoringActivityFactory(
            activity_type='tpm', tpm_partner=None, status=MonitoringActivity.STATUSES.details_configured
        )
        self.assertTrue(ActivityValid(activity, user=self.user).errors)

    def test_empty_partner_for_tpm_activity_in_draft(self):
        activity = MonitoringActivityFactory(activity_type='tpm', tpm_partner=None)
        self.assertFalse(ActivityValid(activity, user=self.user).errors)

    def test_staff_member_from_assigned_partner(self):
        tpm_partner = TPMPartnerFactory()
        activity = MonitoringActivityFactory(activity_type='tpm', tpm_partner=tpm_partner)
        activity.team_members.add(TPMPartnerStaffMemberFactory(tpm_partner=tpm_partner).user)
        self.assertFalse(ActivityValid(activity, user=self.user).errors)

    def test_staff_member_from_other_partner(self):
        activity = MonitoringActivityFactory(activity_type='tpm', tpm_partner=TPMPartnerFactory())
        activity.team_members.add(TPMPartnerStaffMemberFactory(tpm_partner=TPMPartnerFactory()).user)
        self.assertTrue(ActivityValid(activity, user=self.user).errors)
