from __future__ import absolute_import, division, print_function, unicode_literals

from EquiTrack.wrappers import GroupWrapper


class TPMTestCaseMixin(object):
    def setUp(self):
        super(TPMTestCaseMixin, self).setUp()

        # clearing groups cache
        GroupWrapper.invalidate_instances()
