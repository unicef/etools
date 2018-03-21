from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils import six

from EquiTrack.tests.cases import BaseTenantTestCase
from notification.tests.factories import NotificationFactory
from partners.tests.factories import AgreementFactory, PartnerFactory


class TestStrUnicode(BaseTenantTestCase):
    '''Ensure calling six.text_type() on model instances returns the right text.'''

    def test_notification(self):
        agreement = AgreementFactory(partner=PartnerFactory(name=b'xyz'))
        notification = NotificationFactory(sender=agreement)

        self.assertIn(u'Email Notification from', six.text_type(notification))
        self.assertIn(u'for xyz', six.text_type(notification))

        agreement = AgreementFactory(partner=PartnerFactory(name=u'R\xe4dda Barnen'))
        notification = NotificationFactory(sender=agreement)
        self.assertIn(u'Email Notification from', six.text_type(notification))
        self.assertIn(u'for R\xe4dda Barnen', six.text_type(notification))
