from publics.models import EPOCH_ZERO


class AdminListMixin(object):
    exclude_fields = ['id', 'deleted_at']
    custom_fields = ['is_deleted']

    def __init__(self, model, admin_site):
        """
        Gather all the fields from model meta expect fields in 'exclude_fields'.
        Add all fields listed in 'custom_fields'. Those can be admin method, model methods etc.
        """
        self.list_display = [field.name for field in model._meta.fields if field.name not in self.exclude_fields]
        self.search_fields = [field.name for field in model._meta.fields if field.name not in self.exclude_fields]

        self.list_display += self.custom_fields
        self.search_fields += self.custom_fields

        super(AdminListMixin, self).__init__(model, admin_site)

    def queryset(self, request):
        """
        Get queryset from admin_objects to avoid validity filtering.
        """
        return self.model.admin_objects.get_query_set()

    def is_deleted(self, obj):
        """
        Display a deleted indicator on the admin page (green/red tick).
        """
        return obj.deleted_at == EPOCH_ZERO
    is_deleted.short_description = 'Deleted'
    is_deleted.boolean = True
