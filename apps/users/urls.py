from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('register/commercant/', views.register_commercant, name='register_commercant'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('profil/mot-de-passe/', views.changer_mot_de_passe, name='changer_mot_de_passe'),

    # Espace administrateur
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/inscrire/', views.register_admin, name='register_admin'),
    path('admin-dashboard/creer-commercant/', views.creer_commercant, name='creer_commercant'),
    path('admin-dashboard/clients/', views.liste_clients, name='liste_clients'),
    path('admin-dashboard/commercant/<int:pk>/toggle/', views.toggle_actif_commercant, name='toggle_actif_commercant'),
]