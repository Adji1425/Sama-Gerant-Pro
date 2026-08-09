from django.urls import path
from . import views

app_name = 'facturation'

urlpatterns = [
    path('generer/<int:commande_pk>/', views.generer_facture, name='generer_facture'),
    path('<int:pk>/apercu/', views.apercu_facture, name='apercu_facture'),
    path('<int:pk>/telecharger/', views.telecharger_facture, name='telecharger_facture'),
    path('<int:pk>/envoyer-email/', views.envoyer_facture_email, name='envoyer_email'),
]
