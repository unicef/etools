from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
from unittest import skipIf

from EquiTrack.factories import PartnerFactory
from EquiTrack.tests.mixins import EToolsTenantTestCase
from management.models import FlaggedIssue
from management.tests.factories import FlaggedIssueFactory


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(EToolsTenantTestCase):
    def test_flagged_issue(self):
        partner = PartnerFactory()
        issue = FlaggedIssueFactory(
            content_object=partner,
            issue_id="321",
            message='test message'
        )
        self.assertEqual(str(issue), b"test message")
        self.assertEqual(unicode(issue), u"test message")

        issue = FlaggedIssueFactory(
            content_object=partner,
            issue_id="321",
            message=u"R\xe4dda Barnen"
        )
        self.assertEqual(str(issue), b"R\xc3\xa4dda Barnen")
        self.assertEqual(unicode(issue), u"R\xe4dda Barnen")


class FlaggedIssueTest(EToolsTenantTestCase):

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
        issue = FlaggedIssueFactory(
            content_object=partner,
            issue_id=issue_id,
            message='test message'
        )
        self.assertTrue(issue.pk is not None)
        issue_back = FlaggedIssue.get_or_new(partner, issue_id)
        # make sure we got the same one back
        self.assertEqual(issue.pk, issue_back.pk)
