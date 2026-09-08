from django.urls import path
from . import views

app_name = 'sad'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('notifications/<int:pk>/lue/', views.marquer_notification_lue, name='notification_lue'),
    path('notifications/', views.toutes_notifications, name='toutes_notifications'),
    path('stocks-dormants/', views.stocks_dormants_liste, name='stocks_dormants_liste'),

    # Configuration climatique (§5.3.2) — gestion par l'administrateur
    path('climat/', views.liste_climats, name='liste_climats'),
    path('climat/ajouter/', views.creer_climat, name='creer_climat'),
    path('climat/<int:pk>/modifier/', views.modifier_climat, name='modifier_climat'),
    path('climat/<int:pk>/supprimer/', views.supprimer_climat, name='supprimer_climat'),
]
