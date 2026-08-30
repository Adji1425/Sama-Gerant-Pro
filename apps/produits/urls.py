from django.urls import path
from . import views

app_name = 'produits'

urlpatterns = [
    # Public
    path('', views.catalogue, name='catalogue'),
    path('categories/', views.categories, name='categories'),
    path('produit/<int:pk>/', views.fiche_produit, name='fiche_produit'),
    # Favoris (client)
    path('favoris/', views.mes_favoris, name='mes_favoris'),
    path('produit/<int:pk>/favori/', views.toggle_favori, name='toggle_favori'),
    # Commerçant
    path('dashboard/produits/', views.gestion_produits, name='gestion_produits'),
    path('dashboard/produit/ajouter/', views.ajouter_produit, name='ajouter_produit'),
    path('dashboard/produit/<int:pk>/modifier/', views.modifier_produit, name='modifier_produit'),
    path('dashboard/produit/<int:pk>/archiver/', views.archiver_produit, name='archiver_produit'),
    path('dashboard/stock/', views.gestion_stock, name='gestion_stock'),
    path('dashboard/stock/<int:pk>/modifier/', views.modifier_stock, name='modifier_stock'),
    path('dashboard/approvisionnement/ajouter/', views.ajouter_approvisionnement, name='ajouter_appro'),
    path('dashboard/depenses/', views.gestion_depenses, name='gestion_depenses'),
    path('dashboard/depense/ajouter/', views.ajouter_depense, name='ajouter_depense'),
]