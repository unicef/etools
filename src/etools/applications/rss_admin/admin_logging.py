"""
Utility functions for logging changes to Django's LogEntry model.

This module provides functionality to track changes made through RSS admin
in the same way Django admin automatically logs changes.
"""
import json
from typing import Optional

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import force_str


def log_change(
    user,
    obj: models.Model,
    action_flag: int = CHANGE,
    change_message: Optional[str] = None,
    changed_fields: Optional[dict] = None,
) -> LogEntry:
    """
    Log a change to a model instance using Django's LogEntry.

    This mimics the behavior of Django admin's automatic logging.

    Args:
        user: The user making the change
        obj: The model instance being changed
        action_flag: One of ADDITION (1), CHANGE (2), or DELETION (3)
        change_message: Optional custom message describing the change
        changed_fields: Optional dict of field names to (old_value, new_value) tuples
                       to generate a detailed change message

    Returns:
        The created LogEntry instance

    Example:
        >>> log_change(
        ...     user=request.user,
        ...     obj=engagement,
        ...     changed_fields={'financial_findings': (100, 200)}
        ... )
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    object_id = obj.pk

    # Generate change message if not provided
    if change_message is None:
        if changed_fields:
            change_message = _format_change_message(changed_fields)
        elif action_flag == ADDITION:
            change_message = "Added."
        elif action_flag == CHANGE:
            change_message = "Changed."
        elif action_flag == DELETION:
            change_message = "Deleted."
        else:
            change_message = ""

    # Create the log entry
    log_entry = LogEntry.objects.log_action(
        user_id=user.pk if user else None,
        content_type_id=content_type.pk,
        object_id=force_str(object_id),
        object_repr=force_str(obj),
        action_flag=action_flag,
        change_message=change_message,
    )

    return log_entry


def _format_change_message(changed_fields: dict) -> str:
    """
    Format a change message from a dictionary of changed fields.

    Args:
        changed_fields: Dict mapping field names to (old_value, new_value) tuples

    Returns:
        Formatted change message string
    """
    messages = []
    for field_name, (old_value, new_value) in changed_fields.items():
        # Format the values for display
        old_str = _format_value(old_value)
        new_str = _format_value(new_value)

        messages.append(f"{field_name}: {old_str} -> {new_str}")

    return "; ".join(messages)


def _format_value(value) -> str:
    """Format a value for display in change messages."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


def get_changed_fields(old_instance: models.Model, new_instance: models.Model) -> dict:
    """
    Compare two model instances and return a dict of changed fields.

    Args:
        old_instance: The original instance
        new_instance: The updated instance

    Returns:
        Dict mapping field names to (old_value, new_value) tuples
    """
    changed = {}
    model_fields = [f.name for f in old_instance._meta.get_fields() if hasattr(f, 'attname')]

    for field_name in model_fields:
        old_value = getattr(old_instance, field_name, None)
        new_value = getattr(new_instance, field_name, None)

        # Compare values (handling None cases)
        if old_value != new_value:
            changed[field_name] = (old_value, new_value)

    return changed

