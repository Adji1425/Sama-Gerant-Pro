from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from apps.produits.models import Produit, Categorie
from apps.avis.models import Avis


def home(request):
    # Produits par catégorie
    categories = Categorie.objects.all()
    produits_par_categorie = {}
    for cat in categories:
        produits = Produit.objects.filter(
            categorie=cat, statut='actif'
        ).prefetch_related('images')[:4]
        if produits:
            produits_par_categorie[cat.nom] = list(produits)

    # Derniers avis
    derniers_avis = Avis.objects.select_related(
        'client__utilisateur', 'produit'
    ).filter(note__gte=4).order_by('-date_avis')[:3]

    # Stats vitrine
    stats = [
        {'valeur': Produit.objects.filter(statut='actif').count(),
         'label': 'Produits disponibles'},
        {'valeur': categories.count(),
         'label': 'Catégories'},
        {'valeur': Avis.objects.count(),
         'label': 'Avis clients'},
        {'valeur': '100%',
         'label': 'Satisfaction'},
    ]

    # Features
    features = [
        {'icon': '📦', 'titre': 'Stock en temps réel',
         'desc': 'Suivi automatique'},
        {'icon': '📊', 'titre': 'Aide à la décision',
         'desc': 'Graphiques et KPIs'},
        {'icon': '🔔', 'titre': 'Alertes intelligentes',
         'desc': 'Tabaski, Magal…'},
        {'icon': '💬', 'titre': 'Messagerie intégrée',
         'desc': 'Client ↔ Vendeur'},
    ]

    return render(request, 'home.html', {
        'produits_par_categorie': produits_par_categorie,
        'derniers_avis': derniers_avis,
        'stats': stats,
        'features': features,
    })

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
