from django.urls import path
from . import views

app_name = 'avis'

urlpatterns = [
    path('produit/<int:produit_pk>/ajouter/', views.ajouter_avis, name='ajouter_avis'),
    path('<int:pk>/modifier/', views.modifier_avis, name='modifier_avis'),
    path('<int:pk>/supprimer/', views.supprimer_avis, name='supprimer_avis'),
    path('produit/<int:produit_pk>/', views.liste_avis_produit, name='liste_avis'),
]
