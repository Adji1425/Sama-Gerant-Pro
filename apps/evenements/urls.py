from django.urls import path
from . import views

app_name = 'evenements'

urlpatterns = [
    path('', views.liste_evenements, name='liste_evenements'),
    path('ajouter/', views.creer_evenement, name='creer_evenement'),
    path('<int:pk>/modifier/', views.modifier_evenement, name='modifier_evenement'),
    path('<int:pk>/supprimer/', views.supprimer_evenement, name='supprimer_evenement'),
]