from django.contrib import admin

from email_auth.models import SecurityToken


@admin.register(SecurityToken)
class SecurityTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used')
    search_fields = ('user__email', 'token')
    list_filter = ('is_used', )
