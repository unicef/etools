from unicef_restlib.serializers import UserContextSerializerMixin
from unicef_snapshot.models import Activity
from unicef_snapshot.utils import jsonify

from etools.applications.partners.amendment_utils import (
    full_snapshot_instance,
    INTERVENTION_AMENDMENT_IGNORED_FIELDS,
    INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
)


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
            old_value = prev_dict[k]
            new_value = current_dict[k]
            if new_value != old_value:
                if isinstance(new_value, dict):
                    sub_change = create_change_dict_recursive(old_value, new_value)
                    if sub_change:
                        change[k] = sub_change
                elif isinstance(new_value, list) and len(new_value) > 0 and isinstance(new_value[0], dict):
                    sub_change_list = [
                        create_change_dict_recursive(old_value[i], new_value[i])
                        for i in range(len(new_value))
                    ]
                    sub_change_list = [c for c in sub_change_list if c]
                    if sub_change_list:
                        change[k] = sub_change_list
                else:
                    change.update({
                        k: jsonify({
                            "before": old_value,
                            "after": new_value,
                        })
                    })

    return change


class FullInterventionSnapshotSerializerMixin(UserContextSerializerMixin):
    """
    save related model to parent snapshot.
    """

    parent_object_path = ''

    def get_parent_object(self) -> (object, list[str, int]):
        parent_path = []

        instance = self.instance
        for field_name in self.parent_object_path.split('.'):
            field = instance._meta.get_field(field_name)
            parent_path.append((field.remote_field.name, instance.pk))
            instance = getattr(instance, field_name)
        return instance, parent_path

    def save_snapshot(self, target, target_before, current_obj_dict):
        change = create_change_dict_recursive(target_before, current_obj_dict)
        if not change:
            return

        activity_kwargs = {
            'target': target,
            'by_user': self.get_user(),
            'action': Activity.UPDATE,
            'data': target_before,
            'change': change
        }

        snapshot_additional_data = getattr(target, 'snapshot_additional_data', None)
        if callable(snapshot_additional_data):
            activity_kwargs['data'].update(snapshot_additional_data(change))

        Activity.objects.create(**activity_kwargs)

    def save(self, **kwargs):
        target, parent_path = self.get_parent_object()
        target_before = full_snapshot_instance(
            target,
            INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
            INTERVENTION_AMENDMENT_IGNORED_FIELDS,
        )

        instance = super().save(**kwargs)

        current_obj_dict = full_snapshot_instance(
            target.__class__.objects.get(pk=target.pk),
            INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
            INTERVENTION_AMENDMENT_IGNORED_FIELDS,
        )
        self.save_snapshot(target, target_before, current_obj_dict)

        return instance
