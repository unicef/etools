from django.utils.translation import ugettext_lazy as _

from etools.applications.audit.transitions.conditions import BaseTransitionCheck


class ActionPointCompleteActionsTakenCheck(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = super(ActionPointCompleteActionsTakenCheck, self).get_errors(instance, *args, **kwargs)

        if not instance.comments.exists():
            errors['comments'] = _('Please describe actions taken for this action point.')

        return errors
