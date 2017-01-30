from django.db import transaction
from django.forms import model_to_dict

from actstream import action


def create_snapshot_activity_stream(actor, target, created=False):
    """
    Create activity stream for Agreement in order to keep track of field changes
    actor: An activity trigger - Any Python object
    target: An action target for the activity - Mutated but unsaved Django ORM with FieldTracker
    created: A boolean flag that indicates target has been newly created.
    """

    if hasattr(target, 'tracker'):
        with transaction.atomic():
            if created:
                action.send(actor, verb="created",
                            target=target, previous={},
                            changes={})

            else:
                # Get current mutated state of object as dictionary
                current_obj_dict = model_to_dict(target)

                # Get all previous values of mutated fields for current object
                changed_prev_values = target.tracker.changed()

                # Restore the previous state of current object by merging above
                previous = dict(current_obj_dict.items() + changed_prev_values.items())

                # Extract current field changes from key lookups with current object
                changes = {k:v for k,v in current_obj_dict.items() if k in changed_prev_values}

                # Stringify any non-JSON Serializeable data types
                for key, value in previous.items():
                    if type(value) not in [int, float, bool, str]:
                        previous[key] = str(previous[key])

                # Stringify any non-JSON Serializeable data types
                for key, value in changes.items():
                    if type(value) not in [int, float, bool, str]:
                        changes[key] = str(changes[key])

                # TODO: Use a different action verb for each status choice in Agreement
                # Draft, Active, Expired, Suspended, Terminated
                action.send(actor, verb="changed",
                            target=target, previous=previous, changes=changes)
