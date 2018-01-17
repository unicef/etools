from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from unittest import skipIf

from django.utils.six import text_type, binary_type

from EquiTrack.factories import AgreementFactory, NotificationFactory, PartnerFactory
from EquiTrack.tests.mixins import FastTenantTestCase


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(FastTenantTestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_notification(self):
        agreement = AgreementFactory(partner=PartnerFactory(name=b'xyz'))
        notification = NotificationFactory(sender=agreement)
        self.assertIn(b'Email Notification from', binary_type(notification))
        self.assertIn(b'for xyz', binary_type(notification))

        self.assertIn(u'Email Notification from', text_type(notification))
        self.assertIn(u'for xyz', text_type(notification))

        agreement = AgreementFactory(partner=PartnerFactory(name=u'R\xe4dda Barnen'))
        notification = NotificationFactory(sender=agreement)
        self.assertIn(b'Email Notification from', binary_type(notification))
        self.assertIn(b'for R\xc3\xa4dda Barnen', binary_type(notification))

        self.assertIn(u'Email Notification from', text_type(notification))
        self.assertIn(u'for R\xe4dda Barnen', text_type(notification))
