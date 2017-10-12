from EquiTrack.factories import PartnerFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from management.models import FlaggedIssue


class FlaggedIssueTest(FastTenantTestCase):

    @classmethod
    def tearDownClass(cls):
        FlaggedIssue.objects.all().delete()
        super(FlaggedIssueTest, cls).tearDownClass()

    def test_get_or_new_creates_new_unsaved(self):
        partner = PartnerFactory()
        issue = FlaggedIssue.get_or_new(partner, 'test-new-unsaved')
        # make sure we got a new one
        self.assertTrue(issue.pk is None)

    def test_get_or_new_returns_saved(self):
        issue_id = 'test-return-saved'
        partner = PartnerFactory()
        issue = FlaggedIssue.objects.create(content_object=partner, issue_id=issue_id, message='test message')
        self.assertTrue(issue.pk is not None)
        issue_back = FlaggedIssue.get_or_new(partner, issue_id)
        # make sure we got the same one back
        self.assertEqual(issue.pk, issue_back.pk)
