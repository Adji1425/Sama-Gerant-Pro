from django.contrib import admin
from .models import Categorie, Produit, ImageProd, Depense, Favori


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


class ImageProdInline(admin.TabularInline):
    model = ImageProd
    extra = 1


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'commercant', 'categorie', 'prix_vente', 'quantite', 'statut', 'alerte')
    list_filter = ('statut', 'categorie')
    search_fields = ('nom', 'commercant__nom_boutique')
    inlines = [ImageProdInline]

    def alerte(self, obj):
        return obj.est_en_alerte()
    alerte.boolean = True
    alerte.short_description = "En alerte"

@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ('type', 'montant', 'date', 'commercant')
    list_filter = ('type',)


@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ('client', 'produit', 'date_ajout')
    list_filter = ('date_ajout',)
