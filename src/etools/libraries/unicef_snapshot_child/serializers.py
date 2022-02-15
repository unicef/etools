from unicef_restlib.serializers import UserContextSerializerMixin
from unicef_snapshot.models import Activity
from unicef_snapshot.utils import create_change_dict, create_dict_with_relations


class ChildRelatedModelSnapshotSerializerMixin(UserContextSerializerMixin):
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

    def save_snapshot(self, target_before, current_obj_dict):
        change = create_change_dict(target_before, current_obj_dict)
        if not change:
            return

        target, parent_path = self.get_parent_object()

        activity_kwargs = {
            'target': target,
            'by_user': self.get_user(),
            'action': Activity.UPDATE,
            'data': current_obj_dict,
            'change': change
        }

        snapshot_additional_data = getattr(target, 'snapshot_additional_data', None)
        if callable(snapshot_additional_data):
            activity_kwargs['data'].update(snapshot_additional_data(change))

        # wrap data & change with path structure
        for field_name, child_pk in parent_path:
            activity_kwargs['data'] = {field_name: {child_pk: activity_kwargs['data']}}
            activity_kwargs['change'] = {field_name: {child_pk: activity_kwargs['change']}}

        Activity.objects.create(**activity_kwargs)

    def save(self, **kwargs):
        target_before = create_dict_with_relations(self.instance)

        instance = super().save(**kwargs)

        current_obj_dict = create_dict_with_relations(instance)
        self.save_snapshot(target_before, current_obj_dict)

        return self.instance
