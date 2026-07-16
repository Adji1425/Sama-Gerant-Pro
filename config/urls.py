from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('produits/', include('apps.produits.urls')),
    path('users/', include('apps.users.urls')),
    path('commandes/', include('apps.commandes.urls')),
    path('facturation/', include('apps.facturation.urls')),
    path('messagerie/', include('apps.messagerie.urls')),
    path('avis/', include('apps.avis.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('sad/', include('apps.sad.urls')),
    path('evenements/', include('apps.evenements.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
