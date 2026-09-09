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

    # Nouveautés — 8 derniers produits actifs ajoutés (les plus récents)
    nouveautes = Produit.objects.filter(
        statut='actif'
    ).prefetch_related('images').select_related(
        'categorie', 'commercant'
    ).order_by('-date_creation')[:8]

    nouveautes_ids = [p.id for p in nouveautes]

    # Populaires — produits les PLUS VENDUS (quantité totale sur des
    # commandes livrées), pas les plus récents ni les plus notés. On
    # exclut explicitement les nouveautés déjà affichées ci-dessus pour
    # ne jamais montrer deux fois le même produit sur la page d'accueil.
    from django.db.models import Sum, Q as Qf

    populaires = list(
        Produit.objects.filter(
            statut='actif'
        ).exclude(
            id__in=nouveautes_ids
        ).annotate(
            quantite_vendue=Sum(
                'lignepanier__quantite',
                filter=Qf(lignepanier__commande__statut='livree')
            )
        ).filter(
            quantite_vendue__gt=0
        ).prefetch_related('images').select_related(
            'categorie', 'commercant'
        ).order_by('-quantite_vendue')[:8]
    )

    # Boutique récente / peu de ventes : on complète avec les produits
    # actifs restants (toujours hors nouveautés déjà affichées et hors
    # produits populaires déjà retenus), pour ne pas laisser la section
    # vide en attendant les premières ventes.
    if len(populaires) < 8:
        ids_deja_affiches = nouveautes_ids + [p.id for p in populaires]
        complement = Produit.objects.filter(
            statut='actif'
        ).exclude(
            id__in=ids_deja_affiches
        ).prefetch_related('images').select_related(
            'categorie', 'commercant'
        ).order_by('-date_creation')[:8 - len(populaires)]
        populaires = populaires + list(complement)

    # Derniers avis 2 étoiles et +
    derniers_avis = Avis.objects.select_related(
        'client__utilisateur', 'produit'
    ).filter(note__gte=2).order_by('-date_avis')[:3]

    # Stats
       # Stats — calculées à partir des vraies données (aucune valeur figée)
    from django.db.models import Avg

    note_moyenne_globale = Avis.objects.aggregate(moyenne=Avg('note'))['moyenne']

    stats = [
        {
            'valeur': f"{Produit.objects.filter(statut='actif').count()}+",
            'label': 'Produits'
        },
        {
            # Clients distincts (pas juste le nombre d'avis) ayant laissé
            # une note de 4 ou 5 étoiles.
            'valeur': f"{Avis.objects.filter(note__gte=4).values('client').distinct().count()}+",
            'label': 'Clients satisfaits'
        },
        {
            'valeur': f"{note_moyenne_globale:.1f} ★" if note_moyenne_globale is not None else "— ★",
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