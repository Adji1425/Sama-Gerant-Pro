from django.contrib import admin
from .models import Produit, Categorie, ImageProd, OffreProduit, Depense

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prix_vente', 'quantite', 'statut', 'commercant')
    list_filter = ('statut', 'categorie')
    search_fields = ('nom',)

admin.site.register(Categorie)
admin.site.register(ImageProd)
admin.site.register(OffreProduit)
admin.site.register(Depense)