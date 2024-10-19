from etools.applications.governments.models import GDD
from etools.applications.governments.amendment_utils import (
    full_snapshot_instance,
    GDD_FULL_SNAPSHOT_IGNORED_FIELDS,
    GDD_FULL_SNAPSHOT_RELATED_FIELDS,
)
from etools.applications.governments.serializers.gdd_snapshot import save_snapshot

class FullGDDSnapshotDeleteMixin:
    """
    Save full intervention snapshot on delete.
    """

    def get_intervention(self):
        raise NotImplementedError

    def prefetch_relations(self, instance: object) -> GDD:
        return GDD.objects.full_snapshot_qs().get(pk=instance.pk)

    def delete(self, request, *args, **kwargs):
        target = self.get_intervention()
        target_before = full_snapshot_instance(
            self.prefetch_relations(target),
            GDD_FULL_SNAPSHOT_RELATED_FIELDS,
            GDD_FULL_SNAPSHOT_IGNORED_FIELDS,
        )

        response = super().delete(request, *args, **kwargs)

        # refresh instance to avoid cached relations
        target = self.prefetch_relations(target)

        current_obj_dict = full_snapshot_instance(
            target,
            GDD_FULL_SNAPSHOT_RELATED_FIELDS,
            GDD_FULL_SNAPSHOT_IGNORED_FIELDS,
        )
        save_snapshot(request.user, target, target_before, current_obj_dict)

        return response
