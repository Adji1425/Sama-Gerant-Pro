from django.urls import path
from . import views

app_name = 'messagerie'

urlpatterns = [
    path('', views.liste_conversations, name='liste_conversations'),
    path('conversation/<int:conv_id>/', views.chat, name='chat'),
    path('demarrer/<int:commercant_id>/', views.demarrer_conversation, name='demarrer'),
] 