from audit.transitions.conditions import BaseRequiredFieldsCheck


class ActionPointCompleteRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = ['action_taken', ]
