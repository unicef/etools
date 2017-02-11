from django.db import transaction
from django.forms import model_to_dict

from actstream import action


def create_snapshot_activity_stream(actor, target, created=False, delta_dict={}):
    """
    Create activity stream item for Django model instance in order to keep track of field changes
    actor: An activity trigger - Any Python object
    target: An action target for the activity - Mutated but unsaved Django ORM with FieldTracker
    created: A boolean flag that indicates target has been newly created.
    delta_dict: A Python dictionary that contains a set of delta values as a manual method.

    Instance from Serializer class does not trigger FieldTracker.
    Therefore, create_snapshot_activity_stream needs to be able to get instance object and changed dictionary as a manual effort.
    """

    if created:
        action.send(actor, verb="created",
                    target=target, previous={},
                    changes={})

    elif hasattr(target, 'tracker'):
        with transaction.atomic():
            # Get current mutated state of object as dictionary
            current_obj_dict = model_to_dict(target)

            # Get all previous values of mutated fields for current object
            changed_prev_values = target.tracker.changed()

            # If there is no manual delta data passed in, use FieldTracker
            if not delta_dict:
                # Restore the previous state of current object by merging above
                previous = dict(current_obj_dict.items() + changed_prev_values.items())

                # Extract current field changes from key lookups with current object
                changes = {k: v for k, v in current_obj_dict.items() if k in changed_prev_values}

            else:
                previous = current_obj_dict
                changes = {k: v for k, v in delta_dict.items() if k in current_obj_dict and delta_dict[k] != current_obj_dict[k]}

            # Stringify any non-JSON Serializeable data types for previous
            print previous
            for key, value in previous.items():
                if type(value) not in [int, float, bool, str]:
                    try:
                        previous[key] = str(previous[key])
                    except:
                        pass

            # Stringify any non-JSON Serializeable data types for changes
            for key, value in changes.items():
                if type(value) not in [int, float, bool, str]:
                    changes[key] = str(changes[key])

            # We only want to generate a new activity stream item if there is field changes
            if changes:
                # TODO: Use a different action verb for each status choice in Agreement
                # Draft, Active, Expired, Suspended, Terminated
                action.send(actor, verb="changed",
                            target=target, previous=previous, changes=changes)
