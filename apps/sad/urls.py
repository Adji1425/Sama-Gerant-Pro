from django.urls import path
from . import views

app_name = 'sad'

urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('notifications/<int:pk>/lue/', views.marquer_notification_lue, name='notification_lue'),
]

