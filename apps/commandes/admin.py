from django.contrib import admin
from .models import Panier, LignePanier, Commande, Region


class LignePanierInline(admin.TabularInline):
    """Affiche les lignes rattachées à une commande directement dans sa fiche admin"""
    model = LignePanier
    extra = 0
    fields = ('produit', 'quantite', 'prix_unitaire_vente', 'offre')


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'statut', 'region', 'commune', 'montant_total', 'date_commande')
    list_filter = ('statut', 'region')
    inlines = [LignePanierInline]


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


admin.site.register(Panier)
admin.site.register(LignePanier)
