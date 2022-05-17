from etools.applications.partners.amendment_utils import (
    full_snapshot_instance,
    INTERVENTION_FULL_SNAPSHOT_IGNORED_FIELDS,
    INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
)
from etools.applications.partners.models import Intervention
from etools.applications.partners.serializers.intervention_snapshot import save_snapshot


class FullInterventionSnapshotDeleteMixin:
    """
    Save full intervention snapshot on delete.
    """

    def get_intervention(self) -> Intervention:
        raise NotImplementedError

    def prefetch_relations(self, instance: object) -> Intervention:
        return Intervention.objects.full_snapshot_qs().get(pk=instance.pk)

    def delete(self, request, *args, **kwargs):
        target = self.get_intervention()
        target_before = full_snapshot_instance(
            self.prefetch_relations(target),
            INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
            INTERVENTION_FULL_SNAPSHOT_IGNORED_FIELDS,
        )

        response = super().delete(request, *args, **kwargs)

        # refresh instance to avoid cached relations
        target = self.prefetch_relations(target)

        current_obj_dict = full_snapshot_instance(
            target,
            INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
            INTERVENTION_FULL_SNAPSHOT_IGNORED_FIELDS,
        )
        save_snapshot(request.user, target, target_before, current_obj_dict)

        return response
