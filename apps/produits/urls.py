from django.urls import path
from . import views

app_name = 'produits'

urlpatterns = [
    path('', views.catalogue, name='catalogue'),
    path('produit/<int:pk>/', views.fiche_produit, name='fiche_produit'),
]