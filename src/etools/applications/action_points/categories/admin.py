from django.contrib import admin

from etools.applications.action_points.categories.models import Category


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('module', 'description')
    list_filter = ('module', )
    search_fields = ('description', )


admin.site.register(Category, CategoryAdmin)
