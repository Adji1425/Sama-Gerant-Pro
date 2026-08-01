from django.urls import path
from . import views

app_name = 'commandes'

urlpatterns = [
    # Client
    path('panier/', views.voir_panier, name='voir_panier'),
    path('panier/ajouter/<int:produit_id>/', views.ajouter_panier, name='ajouter_panier'),
    path('panier/modifier/<int:ligne_id>/', views.modifier_panier, name='modifier_panier'),
    path('panier/supprimer/<int:ligne_id>/', views.supprimer_panier, name='supprimer_panier'),
    path('valider/', views.valider_commande, name='valider_commande'),
    path('confirmation/<int:commande_id>/', views.confirmation, name='confirmation'),
    path('mes-commandes/', views.mes_commandes, name='mes_commandes'),
    path('commande/<int:commande_id>/', views.detail_commande, name='detail_commande'),
    path('commande/<int:commande_id>/statut/', views.get_statut_json, name='get_statut'),
    # Commerçant
    path('dashboard/commandes/', views.commandes_commercant, name='commandes_commercant'),
    path('dashboard/commande/<int:commande_id>/', views.detail_commande_commercant, name='detail_commande_commercant'),
    path('dashboard/commande/<int:commande_id>/statut/', views.changer_statut, name='changer_statut'),
    path('dashboard/commande/<int:commande_id>/facture/', views.generer_facture, name='generer_facture'),
]