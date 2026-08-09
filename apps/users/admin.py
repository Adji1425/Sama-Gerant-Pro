from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, Client, Commercant, Administrateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active')
    actions = ['bloquer_comptes', 'debloquer_comptes']

    fieldsets = UserAdmin.fieldsets + (
        ('Informations Sama-Gérant Pro', {
            'fields': ('telephone', 'adresse', 'role', 'photo_profile'),
        }),
    )

    def bloquer_comptes(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} compte(s) bloqué(s).")
    bloquer_comptes.short_description = "Bloquer les comptes sélectionnés"

    def debloquer_comptes(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} compte(s) débloqué(s).")
    debloquer_comptes.short_description = "Débloquer les comptes sélectionnés"

    # Note : la réinitialisation de mot de passe est déjà disponible nativement
    # dans Django admin via le lien "This user has no usable password" / "change password"
    # sur la fiche de chaque utilisateur — pas besoin de code supplémentaire.


admin.site.register(Client)
admin.site.register(Commercant)
admin.site.register(Administrateur)
