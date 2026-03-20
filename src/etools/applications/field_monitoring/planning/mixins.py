from django.db import models
from django.utils.translation import gettext_lazy as _

from django_fsm import transition as transition_wrapper

from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result, ResultType


class EWPActivity(models.Model):
    wbs = models.CharField(max_length=255)
    cp_output = models.ForeignKey(Result, null=True, blank=True, verbose_name=_('CP Output'),
                                  on_delete=models.SET_NULL, related_name='ewp_activities')
    activity = models.ForeignKey(
        Result,
        null=True,
        blank=True,
        verbose_name=_('Activity'),
        on_delete=models.PROTECT,
        related_name='fm_ewp_activities',
        limit_choices_to={'result_type__name': ResultType.ACTIVITY},
    )

    class Meta:
        app_label = 'field_monitoring_planning'
        constraints = [
            # When cp_output is set: (wbs, cp_output) must be unique.
            models.UniqueConstraint(
                fields=['wbs', 'cp_output'],
                condition=models.Q(cp_output__isnull=False),
                name='unique_ewpactivity_wbs_cp_output',
            ),
            # When cp_output is NULL: wbs alone must be unique.
            # (standard UNIQUE constraints treat NULLs as distinct in PostgreSQL,
            # so this partial index is required to actually enforce uniqueness.)
            models.UniqueConstraint(
                fields=['wbs'],
                condition=models.Q(cp_output__isnull=True),
                name='unique_ewpactivity_wbs_null_cp_output',
            ),
        ]

    def __str__(self):
        return self.wbs


# ---------------------------------------------------------------------------
# Target-field constants shared across models, serializers and offline helpers
# ---------------------------------------------------------------------------

# (m2m_relation_name, question_level, target_field_name) for the two "simple"
# relations that don't need special deduplication logic.
STANDARD_TARGET_MAPPINGS = [
    ('partners', 'partner', 'partner'),
    ('interventions', 'intervention', 'intervention'),
]

# Ordered tuple of all target field names used for overall/checklist findings.
ACTIVITY_TARGET_FIELDS = ('partner', 'cp_output', 'intervention', 'ewp_activity')


class QuestionTargetMixin(models.Model):
    partner = models.ForeignKey(PartnerOrganization, blank=True, null=True, verbose_name=_('Partner'),
                                on_delete=models.CASCADE, related_name='+')
    cp_output = models.ForeignKey(Result, blank=True, null=True, verbose_name=_('CP Output'),
                                  on_delete=models.CASCADE, related_name='+')
    intervention = models.ForeignKey(Intervention, blank=True, null=True, verbose_name=_('Intervention'),
                                     on_delete=models.CASCADE, related_name='+')
    ewp_activity = models.ForeignKey(EWPActivity, null=True, blank=True, verbose_name=_('eWP Activity'),
                                     on_delete=models.PROTECT, related_name='+')

    @property
    def related_to(self):
        return self.partner or self.cp_output or self.intervention

    class Meta:
        abstract = True


class ProtectUnknownTransitionsMeta(type):
    """
    Metaclass to disallow all transitions except defined ones
    """

    def __new__(cls, name, bases, new_attrs, **kwargs):
        status_field = new_attrs['status']

        choices = dict(status_field.choices).keys()
        statuses_matrix = {
            (source, target): False for source in choices for target in choices if source != target
        }

        for attr in new_attrs.values():
            if not hasattr(attr, '_django_fsm'):
                continue

            for transition in attr._django_fsm.transitions.values():
                statuses_matrix[(transition.source, transition.target)] = True

        for transition, known in statuses_matrix.items():
            if known:
                continue

            def new_transition(self):
                pass
            new_transition.__name__ = 'transition_{}_{}'.format(*transition)

            def access_denied_permission(instance, user):
                return False

            new_attrs[new_transition.__name__] = transition_wrapper(
                'status', transition[0], target=transition[1], permission=access_denied_permission
            )(new_transition)

        return super().__new__(cls, name, bases, new_attrs, **kwargs)


class EmptyQuerysetForExternal:
    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_unicef_user():
            return queryset.none()

        return queryset
