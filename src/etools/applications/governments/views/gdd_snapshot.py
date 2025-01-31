from etools.applications.governments.amendment_utils import (
    GDD_FULL_SNAPSHOT_IGNORED_FIELDS,
    GDD_FULL_SNAPSHOT_RELATED_FIELDS,
)
from etools.applications.governments.models import GDD
from etools.applications.governments.serializers.gdd_snapshot import save_snapshot
from etools.applications.partners.amendment_utils import full_snapshot_instance


class FullGDDSnapshotDeleteMixin:
    """
    Save full GDD snapshot on delete.
    """

    def get_gdd(self):
        raise NotImplementedError

    def prefetch_relations(self, instance: object) -> GDD:
        return GDD.objects.full_snapshot_qs().get(pk=instance.pk)

    def delete(self, request, *args, **kwargs):
        target = self.get_gdd()
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
