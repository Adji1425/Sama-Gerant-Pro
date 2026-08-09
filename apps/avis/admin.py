from django.contrib import admin
from .models import Avis


@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = ('produit', 'client', 'note', 'verifie_achat', 'date_avis')
    list_filter = ('note', 'verifie_achat')
    search_fields = ('produit__nom', 'client__utilisateur__username')
    actions = ['moderer_supprimer']

    def moderer_supprimer(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} avis supprimé(s).")
    moderer_supprimer.short_description = "Supprimer les avis sélectionnés (modération)"
