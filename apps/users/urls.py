from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
]