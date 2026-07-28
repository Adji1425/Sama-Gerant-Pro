from django.shortcuts import render, get_object_or_404
from .models import Produit, Categorie


def catalogue(request):
    """Page catalogue publique — accessible sans connexion."""
    produits = Produit.objects.filter(
        statut='actif'
    ).prefetch_related('images').select_related('categorie')

    categories = Categorie.objects.all()

    recherche = request.GET.get('q', '')
    if recherche:
        produits = produits.filter(nom__icontains=recherche)

    categorie_id = request.GET.get('categorie', '')
    if categorie_id:
        produits = produits.filter(categorie__id=categorie_id)

    context = {
        'produits': produits,
        'categories': categories,
        'recherche': recherche,
        'categorie_selectionnee': categorie_id,
    }
    return render(request, 'produits/catalogue.html', context)


def fiche_produit(request, pk):
    """Page détail produit — accessible sans connexion."""
    produit = get_object_or_404(Produit, pk=pk, statut='actif')
    images = produit.images.all()
    avis = produit.avis_set.all().select_related('client__utilisateur')

    avis_client = None
    peut_noter = False

    if request.user.is_authenticated and hasattr(request.user, 'client'):
        from apps.avis.models import Avis
        from apps.commandes.models import LignePanier  # ✅ CORRIGÉ

        avis_client = Avis.objects.filter(
            client=request.user.client,
            produit=produit
        ).first()

        # ✅ CORRIGÉ : vérif via LignePanier (commande validée et livrée)
        a_achete = LignePanier.objects.filter(
            panier__client=request.user.client,
            produit=produit,
            commande__isnull=False,
            commande__statut='livree'
        ).exists()

        peut_noter = a_achete and not avis_client

    context = {
        'produit': produit,
        'images': images,
        'avis': avis,
        'avis_client': avis_client,
        'peut_noter': peut_noter,
        'note_moyenne': produit.note_moyenne(),
        'offre': getattr(produit, 'offre', None),
    }
    return render(request, 'produits/fiche_produit.html', context)