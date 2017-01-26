import datetime

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from EquiTrack.factories import AgreementFactory

from partners.models import Agreement

from actstream.signals import action
from actstream.tests.base import DataTestCase


class CustomDataFeedTestCase(DataTestCase):
    actstream_models = ('partners.Agreement', 'sites.Site')

    def setUp(self):
        super(CustomDataFeedTestCase, self).setUp()

        self.agreement = AgreementFactory()
        self.agreement_content_type = ContentType.objects.get_for_model(Agreement)

        action.send(self.user1, verb="created",
                    target=self.agreement)

    def test_json_feed(self):
        self.agreement.start = None
        self.agreement.end = None

        Agreement.create_snapshot_activity_stream(self.user1, self.agreement)

        expected = [
            "admin created %s" % self.agreement,
            "admin changed %s" % self.agreement,
        ]

        json_feed = self.capture('actstream_model_feed_json', self.agreement_content_type.pk)
