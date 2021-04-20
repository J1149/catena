from django.contrib import admin

from django_messages.utils import get_user_model
CatenaUser = get_user_model()


class CatenaUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'public_key', 'full_name', 'account_type', 'paipass_user_id', 'last_login', 'date_joined')
    exclude = ('password', 'description', 'full_name', 'access_token')
admin.site.register(CatenaUser, CatenaUserAdmin)
