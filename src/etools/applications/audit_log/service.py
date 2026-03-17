import logging
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from etools.applications.audit_log.models import AuditLogEntry
from etools.applications.core.middleware import get_current_user
from etools.applications.environment.helpers import tenant_switch_is_active

logger = logging.getLogger(__name__)

AUDIT_LOG_SWITCH = 'audit_log_enabled'

SKIPPED_FIELDS = frozenset({'id', 'created', 'modified', 'proof_file', 'waybill_file'})


def audit_log(instance, action, user=None, old_instance=None,
              changed_fields=None, old_values=None, new_values=None,
              description='', fields=None):
    """Log an audit entry for a model instance.

    Args:
        instance: The model instance.
        action: 'CREATE', 'UPDATE', 'DELETE', or 'SOFT_DELETE'.
        user: Who made the change. Falls back to get_current_user().
        old_instance: For UPDATE auto-diff — a snapshot of the old state.
        changed_fields: Explicit list of changed field names (skips auto-diff).
        old_values: Explicit dict of old values (skips auto-diff).
        new_values: Explicit dict of new values (skips auto-diff).
        description: Optional human-readable description.
        fields: Limit which fields to serialize. None = all concrete fields.
    """
    if not tenant_switch_is_active(AUDIT_LOG_SWITCH):
        return
    try:
        _audit_log(instance, action, user, old_instance,
                   changed_fields, old_values, new_values, description, fields)
    except Exception:
        logger.exception(
            "Failed to create audit log for %s #%s",
            type(instance).__name__, instance.pk,
        )


def _audit_log(instance, action, user, old_instance,
               changed_fields, old_values, new_values, description, fields):
    ct = ContentType.objects.get_for_model(instance)
    user = user or get_current_user()

    if action == AuditLogEntry.ACTION_CREATE:
        concrete = _get_concrete_fields(type(instance), fields)
        new_values = _serialize_fields(instance, concrete)
        changed_fields = None
        old_values = None

    elif action == AuditLogEntry.ACTION_UPDATE:
        if changed_fields is not None or old_values is not None or new_values is not None:
            pass  # use explicit values as-is
        elif old_instance:
            concrete = _get_concrete_fields(type(instance), fields)
            changed_fields, old_values, new_values = _compute_diff(
                old_instance, instance, concrete,
            )
            if not changed_fields:
                return  # nothing changed
        else:
            return  # no old_instance and no explicit values — nothing to log

    elif action in (AuditLogEntry.ACTION_DELETE, AuditLogEntry.ACTION_SOFT_DELETE):
        concrete = _get_concrete_fields(type(instance), fields)
        old_values = _serialize_fields(instance, concrete)
        changed_fields = None
        new_values = None

    with transaction.atomic():
        AuditLogEntry.objects.create(
            content_type=ct,
            object_id=str(instance.pk),
            action=action,
            changed_fields=changed_fields,
            old_values=old_values,
            new_values=new_values,
            user=user,
            description=description,
        )


def bulk_audit_log(queryset, action, user=None, description=''):
    if not tenant_switch_is_active(AUDIT_LOG_SWITCH):
        return
    try:
        if not queryset.exists():
            return
        model_class = queryset.model
        ct = ContentType.objects.get_for_model(model_class)
        user = user or get_current_user()
        concrete = _get_concrete_fields(model_class)
        entries = []
        for obj in queryset:
            old_values = _serialize_fields(obj, concrete) if action in (
                AuditLogEntry.ACTION_DELETE, AuditLogEntry.ACTION_SOFT_DELETE,
            ) else None
            entries.append(AuditLogEntry(
                content_type=ct,
                object_id=str(obj.pk),
                action=action,
                old_values=old_values,
                user=user,
                description=description,
            ))
        with transaction.atomic():
            AuditLogEntry.objects.bulk_create(entries)
    except Exception:
        logger.exception("Failed to bulk create audit logs for %s", model_class.__name__)


def _get_concrete_fields(model_class, fields=None):
    if fields:
        return set(fields)
    return {f.attname for f in model_class._meta.get_fields() if hasattr(f, 'attname') and hasattr(f, 'column') and not getattr(f, 'many_to_many', False)} - SKIPPED_FIELDS


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str, list, dict)):
        return value
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _serialize_fields(instance, fields):
    values = {}
    for field in fields:
        if hasattr(instance, field):
            try:
                values[field] = _serialize_value(getattr(instance, field))
            except Exception:
                logger.debug("Could not serialize field %s", field)
    return values


def _compute_diff(old_instance, new_instance, fields):
    changed = []
    old_values = {}
    new_values = {}
    for field in fields:
        if not hasattr(old_instance, field) or not hasattr(new_instance, field):
            continue
        old_val = getattr(old_instance, field)
        new_val = getattr(new_instance, field)
        if old_val != new_val:
            changed.append(field)
            old_values[field] = _serialize_value(old_val)
            new_values[field] = _serialize_value(new_val)
    return changed, old_values, new_values
