from __future__ import absolute_import, division, print_function, unicode_literals

from audit.transitions.conditions import BaseRequiredFieldsCheck


class ActionPointCompleteRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = ['action_taken', ]
