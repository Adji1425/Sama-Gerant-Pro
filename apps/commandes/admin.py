from django.contrib import admin
from .models import Panier, LignePanier, Commande

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'statut', 'montant_total', 'date_commande')
    list_filter = ('statut',)

admin.site.register(Panier)
admin.site.register(LignePanier)