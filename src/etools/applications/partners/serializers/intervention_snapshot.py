from unicef_restlib.serializers import UserContextSerializerMixin
from unicef_snapshot.models import Activity
from unicef_snapshot.utils import jsonify

from etools.applications.partners.amendment_utils import (
    full_snapshot_instance,
    INTERVENTION_FULL_SNAPSHOT_IGNORED_FIELDS,
    INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
)
from etools.applications.partners.models import Intervention


def create_change_dict_recursive(prev_dict, current_dict):
    """Create a dictionary showing the differences between the
    initial target and the target after being saved.

    If prev_dict is empty, then change is empty as well
    """
    change = {}
    if prev_dict is not None:
        for k, v in prev_dict.items():
            if k not in current_dict:
                continue
            prev = prev_dict[k]
            new = current_dict[k]
            if new != prev:
                # go deeper in case of inherited dictionary structure
                if isinstance(new, dict):
                    sub_change = create_change_dict_recursive(prev, new)
                    if sub_change:
                        change[k] = sub_change
                # calculate per-element difference in case of dictionaries inside list
                elif isinstance(new, list) and len(new) > 0 and len(new) == len(prev) and isinstance(new[0], dict):
                    sub_change_list = [
                        create_change_dict_recursive(prev[i], new[i])
                        for i in range(len(new))
                    ]
                    sub_change_list = [c for c in sub_change_list if c]
                    if sub_change_list:
                        change[k] = sub_change_list
                else:
                    change.update({
                        k: jsonify({
                            "before": prev,
                            "after": new,
                        })
                    })

    return change


def save_snapshot(user, target, target_before, current_obj_dict):
    change = create_change_dict_recursive(target_before, current_obj_dict)
    if not change:
        return

    activity_kwargs = {
        'target': target,
        'by_user': user,
        'action': Activity.UPDATE,
        'data': target_before,
        'change': change
    }

    snapshot_additional_data = getattr(target, 'snapshot_additional_data', None)
    if callable(snapshot_additional_data):
        activity_kwargs['data'].update(snapshot_additional_data(change))

    Activity.objects.create(**activity_kwargs)


class FullInterventionSnapshotSerializerMixin(UserContextSerializerMixin):
    """
    Save full intervention snapshot on save.
    """

    def get_intervention(self) -> Intervention:
        raise NotImplementedError

    def prefetch_relations(self, instance: object) -> Intervention:
        return Intervention.objects.full_snapshot_qs().get(pk=instance.pk)

    def save(self, **kwargs):
        target = self.get_intervention()
        target_before = full_snapshot_instance(
            self.prefetch_relations(target),
            INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
            INTERVENTION_FULL_SNAPSHOT_IGNORED_FIELDS,
        )

        instance = super().save(**kwargs)

        # refresh instance to avoid cached relations
        target = self.prefetch_relations(target)

        current_obj_dict = full_snapshot_instance(
            target,
            INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
            INTERVENTION_FULL_SNAPSHOT_IGNORED_FIELDS,
        )
        save_snapshot(self.get_user(), target, target_before, current_obj_dict)

        return instance
