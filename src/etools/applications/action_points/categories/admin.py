from django.contrib import admin

from etools.applications.action_points.categories.models import Category
from etools.libraries.djangolib.admin import RestrictedEditAdmin


class CategoryAdmin(RestrictedEditAdmin):
    list_display = ('module', 'description')
    list_filter = ('module', )
    search_fields = ('description', )


admin.site.register(Category, CategoryAdmin)
