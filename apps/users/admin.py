from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, Client, Commercant, Administrateur

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Infos supplémentaires', {
            'fields': ('role', 'telephone', 'adresse', 'photo_profile')
        }),
    )

admin.site.register(Client)
admin.site.register(Commercant)
admin.site.register(Administrateur)