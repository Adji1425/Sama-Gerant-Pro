from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from apps.produits.models import Produit, Categorie, Favori
from apps.avis.models import Avis


def home(request):
    categories = Categorie.objects.all().prefetch_related('produits__images')

    # Photo représentative : le 1er produit actif de la catégorie qui a une image
    for categorie in categories:
        categorie.photo = None
        for produit in categorie.produits.all():
            if produit.statut == 'actif':
                img = produit.image_principale
                if img:
                    categorie.photo = img
                    break

    # Nouveautés — 8 derniers produits actifs
    nouveautes = Produit.objects.filter(
        statut='actif'
    ).prefetch_related('images').select_related(
        'categorie', 'commercant'
    ).order_by('-date_creation')[:8]

    # Populaires — produits avec le + d'avis
    from django.db.models import Count
    populaires = Produit.objects.filter(
        statut='actif'
    ).annotate(
        nb_avis=Count('avis_set')
    ).prefetch_related('images').select_related(
        'categorie', 'commercant'
    ).order_by('-nb_avis', '-date_creation')[:8]

    # Derniers avis 2 étoiles et +
    derniers_avis = Avis.objects.select_related(
        'client__utilisateur', 'produit'
    ).filter(note__gte=2).order_by('-date_avis')[:3]

    # Stats
    stats = [
        {
            'valeur': f"{Produit.objects.filter(statut='actif').count()}+",
            'label': 'Produits'
        },
        {
            'valeur': f"{Avis.objects.filter(note__gte=4).count()}+",
            'label': 'Clients satisfaits'
        },
        {
            'valeur': '5.0 ★',
            'label': 'Note moyenne'
        },
    ]

    # Catégories par défaut si aucune en BDD
    categories_defaut = [
        ('👗', 'Mode'), ('👟', 'Chaussures'),
        ('💄', 'Beauté'), ('⌚', 'Montres'),
        ('📱', 'High-Tech'), ('🏋️', 'Sport'),
    ]

    return render(request, 'home.html', {
        'categories': categories,
        'categories_defaut': categories_defaut,
        'nouveautes': nouveautes,
        'populaires': populaires,
        'derniers_avis': derniers_avis,
        'stats': stats,
        'favoris_ids': list(
            Favori.objects.filter(client=request.user.client).values_list('produit_id', flat=True)
        ) if request.user.is_authenticated and hasattr(request.user, 'client') else [],
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('users/', include('apps.users.urls', namespace='users')),
    path('produits/', include('apps.produits.urls', namespace='produits')),
    path('commandes/', include('apps.commandes.urls', namespace='commandes')),
    path('messagerie/', include('apps.messagerie.urls', namespace='messagerie')),
    # Modules de Mame Diarra — urls.py encore vides, prêts à être remplis
    path('facturation/', include('apps.facturation.urls', namespace='facturation')),
    path('avis/', include('apps.avis.urls', namespace='avis')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('sad/', include('apps.sad.urls', namespace='sad')),
    path('evenements/', include('apps.evenements.urls', namespace='evenements')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)