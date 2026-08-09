from django.contrib import admin
from .models import Panier, LignePanier, Commande


class LignePanierInline(admin.TabularInline):
    """Affiche les lignes rattachées à une commande directement dans sa fiche admin"""
    model = LignePanier
    extra = 0
    fields = ('produit', 'quantite', 'prix_unitaire_vente', 'offre')


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'statut', 'montant_total', 'date_commande')
    list_filter = ('statut',)
    inlines = [LignePanierInline]


admin.site.register(Panier)
admin.site.register(LignePanier)
