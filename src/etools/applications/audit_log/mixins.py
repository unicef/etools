from django.db import models

from etools.applications.audit_log.service import audit_log, bulk_audit_log


def _is_model_instance(obj):
    return isinstance(obj, models.Model)


class AuditLogViewSetMixin:
    """DRF viewset mixin that automatically logs create, update, and delete operations.

    Hooks into ``perform_create``, ``perform_update``, and ``perform_destroy``
    to record audit log entries with old/new diffs.  Also tracks M2M changes.

    Safely skips logging when the serializer returns a non-model instance
    (e.g. a dict from a custom ``create()``).

    Usage::

        from etools.applications.audit_log.mixins import AuditLogViewSetMixin

        class MyViewSet(AuditLogViewSetMixin, ModelViewSet):
            ...
    """

    def perform_create(self, serializer):
        super().perform_create(serializer)
        if _is_model_instance(serializer.instance):
            audit_log(serializer.instance, 'CREATE', user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        if not _is_model_instance(instance):
            super().perform_update(serializer)
            return

        old_instance = type(instance).objects.get(pk=instance.pk)
        m2m_fields = _get_m2m_field_names(type(instance))
        old_m2m = _snapshot_m2m(instance, m2m_fields) if m2m_fields else {}

        super().perform_update(serializer)

        audit_log(instance, 'UPDATE', user=self.request.user, old_instance=old_instance)

        if m2m_fields:
            instance.refresh_from_db()
            new_m2m = _snapshot_m2m(instance, m2m_fields)
            changed_fields = []
            old_values = {}
            new_values = {}
            for field in m2m_fields:
                if old_m2m[field] != new_m2m[field]:
                    changed_fields.append(field)
                    old_values[field] = sorted(old_m2m[field])
                    new_values[field] = sorted(new_m2m[field])
            if changed_fields:
                audit_log(
                    instance, 'UPDATE', user=self.request.user,
                    changed_fields=changed_fields,
                    old_values=old_values,
                    new_values=new_values,
                    description='M2M fields changed',
                )

    def perform_destroy(self, instance):
        audit_log(instance, 'DELETE', user=self.request.user)
        super().perform_destroy(instance)


class ScopedAuditLogMixin:
    """DRF viewset mixin that scopes AuditLogEntry querysets to the current user.

    Applies ``AuditLogEntry.objects.for_user(request.user)`` so users only
    see audit entries for app_labels allowed by their group membership.

    Usage::

        from etools.applications.audit_log.mixins import ScopedAuditLogMixin

        class MyAuditViewSet(ScopedAuditLogMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
            ...
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.for_user(self.request.user)


def _get_m2m_field_names(model):
    return [
        f.name for f in model._meta.get_fields()
        if f.many_to_many and not f.auto_created
    ]


def _snapshot_m2m(obj, m2m_fields):
    return {
        field: set(getattr(obj, field).values_list('pk', flat=True))
        for field in m2m_fields
    }


class AuditModelAdmin:
    """Mixin for ModelAdmin that automatically logs changes via audit_log().

    Logging is controlled by the 'audit_log_enabled' TenantSwitch in the service layer.

    Usage:
        from etools.applications.audit_log.mixins import AuditModelAdmin

        @admin.register(MyModel)
        class MyModelAdmin(AuditModelAdmin, admin.ModelAdmin):
            ...
    """

    def save_model(self, request, obj, form, change):
        if change:
            old_instance = type(obj).objects.get(pk=obj.pk)
        super().save_model(request, obj, form, change)
        if change:
            audit_log(obj, 'UPDATE', user=request.user, old_instance=old_instance)
        else:
            audit_log(obj, 'CREATE', user=request.user)

    def save_related(self, request, form, formsets, change):
        obj = form.instance
        m2m_fields = _get_m2m_field_names(type(obj))
        old_m2m = _snapshot_m2m(obj, m2m_fields) if m2m_fields and change else {}
        super().save_related(request, form, formsets, change)
        if not m2m_fields or not change:
            return
        new_m2m = _snapshot_m2m(obj, m2m_fields)
        changed_fields = []
        old_values = {}
        new_values = {}
        for field in m2m_fields:
            if old_m2m[field] != new_m2m[field]:
                changed_fields.append(field)
                old_values[field] = sorted(old_m2m[field])
                new_values[field] = sorted(new_m2m[field])
        if changed_fields:
            audit_log(
                obj, 'UPDATE', user=request.user,
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                description='M2M fields changed',
            )

    def delete_model(self, request, obj):
        audit_log(obj, 'DELETE', user=request.user)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        bulk_audit_log(queryset, 'DELETE', user=request.user)
        super().delete_queryset(request, queryset)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            audit_log(obj, 'DELETE', user=request.user)
        for obj in instances:
            is_new = obj.pk is None or not type(obj).objects.filter(pk=obj.pk).exists()
            if is_new:
                obj.save()
                audit_log(obj, 'CREATE', user=request.user)
            else:
                old_instance = type(obj).objects.get(pk=obj.pk)
                obj.save()
                audit_log(obj, 'UPDATE', user=request.user, old_instance=old_instance)
        formset.save_m2m()
