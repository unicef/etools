from unicef_restlib.serializers import UserContextSerializerMixin
from unicef_snapshot.models import Activity
from unicef_snapshot.utils import create_change_dict

from etools.applications.partners.amendment_utils import (
    full_snapshot_instance,
    INTERVENTION_AMENDMENT_IGNORED_FIELDS,
    INTERVENTION_FULL_SNAPSHOT_RELATED_FIELDS,
)


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
        change = create_change_dict(target_before, current_obj_dict)
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
