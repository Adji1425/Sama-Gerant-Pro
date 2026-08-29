from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Produit, Categorie, ImageProd, OffreProduit, Depense, Approvisionnement, Favori
from .forms import ProduitForm, OffreProduitForm, DepenseForm, ApprovisionnementForm
from urllib.parse import urlencode

# ── Décorateur commerçant ──────────────────────────────────────────────────────
def commercant_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not hasattr(request.user, 'commercant'):
            messages.error(request, "Accès réservé aux commerçants.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ── VUES PUBLIQUES ────────────────────────────────────────────────────────────
def categories(request):
    """Vue d'ensemble des catégories, avec une photo représentative
    (premier produit actif avec image) et le nombre de produits."""
    categories = Categorie.objects.all().prefetch_related('produits__images')

    for cat in categories:
        cat.nb_produits = cat.produits.filter(statut='actif').count()
        cat.photo = None
        for produit in cat.produits.all():
            if produit.statut == 'actif':
                img = produit.image_principale
                if img:
                    cat.photo = img
                    break

    return render(request, 'produits/categories.html', {
        'categories': categories,
    })


def catalogue(request):
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

    favoris_ids = []
    if request.user.is_authenticated and hasattr(request.user, 'client'):
        favoris_ids = list(
            Favori.objects.filter(client=request.user.client)
            .values_list('produit_id', flat=True)
        )

    return render(request, 'produits/catalogue.html', {
        'produits': produits,
        'categories': categories,
        'recherche': recherche,
        'categorie_selectionnee': categorie_id,
        'favoris_ids': favoris_ids,
    })


def fiche_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk, statut='actif')
    images = produit.images.all()
    avis = produit.avis_set.all().select_related('client__utilisateur')

    avis_client = None
    peut_noter = False
    if request.user.is_authenticated and hasattr(request.user, 'client'):
        from apps.avis.models import Avis
        from apps.commandes.models import LignePanier
        avis_client = Avis.objects.filter(
            client=request.user.client, produit=produit
        ).first()
        a_achete = LignePanier.objects.filter(
            panier__client=request.user.client,
            produit=produit,
            commande__isnull=False,
            commande__statut='livree'
        ).exists()
        peut_noter = a_achete and not avis_client

    est_favori = False
    if request.user.is_authenticated and hasattr(request.user, 'client'):
        est_favori = Favori.objects.filter(
            client=request.user.client, produit=produit
        ).exists()

    return render(request, 'produits/fiche_produit.html', {
        'produit': produit,
        'images': images,
        'avis': avis,
        'avis_client': avis_client,
        'peut_noter': peut_noter,
        'note_moyenne': produit.note_moyenne(),
        'offre': getattr(produit, 'offre', None),
        'est_favori': est_favori,
    })


# ── GESTION PRODUITS (Commerçant) ─────────────────────────────────────────────
@commercant_required
def gestion_produits(request):
    commercant = request.user.commercant
    produits = Produit.objects.filter(
        commercant=commercant
    ).select_related('categorie').order_by('-date_creation')

    # KPI calculés sur l'ensemble des produits du commerçant, avant filtrage
    total_actifs = produits.filter(statut='actif').count()
    total_archives = produits.filter(statut='archive').count()
    en_alerte = [p for p in produits if p.est_en_alerte()]

    # Filtre par statut (pastilles, comme pour les commandes)
    statut_filtre = request.GET.get('statut', '')
    if statut_filtre:
        produits = produits.filter(statut=statut_filtre)

    # Recherche par nom, pour retrouver vite un produit quand il y en a beaucoup
    recherche = request.GET.get('q', '').strip()
    if recherche:
        produits = produits.filter(nom__icontains=recherche)

    # Filtre par catégorie
    categorie_filtre = request.GET.get('categorie', '').strip()
    if categorie_filtre:
        produits = produits.filter(categorie_id=categorie_filtre)

    extra_params = {}
    if recherche:
        extra_params['q'] = recherche
    if categorie_filtre:
        extra_params['categorie'] = categorie_filtre
    extra_qs = urlencode(extra_params)

    return render(request, 'produits/gestion_produits.html', {
        'produits': produits,
        'total_actifs': total_actifs,
        'total_archives': total_archives,
        'en_alerte': en_alerte,
        'statut_filtre': statut_filtre,
        'recherche': recherche,
        'categorie_filtre': categorie_filtre,
        'categories': Categorie.objects.filter(
            produits__commercant=commercant
        ).distinct().order_by('nom'),
        'extra_qs': extra_qs,
    })


@commercant_required
def ajouter_produit(request):
    if request.method == 'POST':
        form = ProduitForm(request.POST)
        if form.is_valid():
            produit = form.save(commit=False)
            produit.commercant = request.user.commercant
            produit.save()

            # Gérer les images uploadées
            images = request.FILES.getlist('images')
            for i, img in enumerate(images):
                ImageProd.objects.create(
                    produit=produit,
                    image=img,
                    est_principale=(i == 0)
                )

            messages.success(request, f"✓ Produit '{produit.nom}' ajouté avec succès !")
            return redirect('produits:gestion_produits')
        else:
            messages.error(request, "Veuillez corriger les erreurs.")
    else:
        form = ProduitForm()

    return render(request, 'produits/ajouter_produit.html', {'form': form})


@commercant_required
def modifier_produit(request, pk):
    produit = get_object_or_404(
        Produit, pk=pk, commercant=request.user.commercant
    )

    if request.method == 'POST':
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            form.save()

            # Nouvelles images
            nouvelles_images = request.FILES.getlist('images')
            for img in nouvelles_images:
                ImageProd.objects.create(produit=produit, image=img)

            messages.success(request, "✓ Produit modifié avec succès !")
            return redirect('produits:gestion_produits')
    else:
        form = ProduitForm(instance=produit)

    return render(request, 'produits/modifier_produit.html', {
        'form': form, 'produit': produit
    })


@commercant_required
def archiver_produit(request, pk):
    produit = get_object_or_404(
        Produit, pk=pk, commercant=request.user.commercant
    )
    if produit.statut == 'actif':
        produit.statut = 'archive'
        messages.info(request, f"'{produit.nom}' archivé.")
    else:
        produit.statut = 'actif'
        messages.success(request, f"'{produit.nom}' réactivé.")
    produit.save()
    return redirect('produits:gestion_produits')


# ── STOCK ─────────────────────────────────────────────────────────────────────
@commercant_required
def gestion_stock(request):
    commercant = request.user.commercant
    produits = Produit.objects.filter(
        commercant=commercant, statut='actif'
    ).order_by('quantite')

    return render(request, 'produits/gestion_stock.html', {
        'produits': produits,
        'en_alerte': [p for p in produits if p.est_en_alerte()],
        'approvisionnements': Approvisionnement.objects.filter(
            commercant=commercant
        ).select_related('produit').order_by('-date_approvisionnement')[:10],
    })


@commercant_required
def modifier_stock(request, pk):
    produit = get_object_or_404(
        Produit, pk=pk, commercant=request.user.commercant
    )
    if request.method == 'POST':
        nouvelle_qte = request.POST.get('quantite')
        if nouvelle_qte:
            produit.quantite = int(nouvelle_qte)
            produit.save()
            messages.success(
                request,
                f"Stock de '{produit.nom}' mis à jour : {produit.quantite} unité(s)."
            )
    return redirect('produits:gestion_stock')


@commercant_required
def ajouter_approvisionnement(request):
    if request.method == 'POST':
        form = ApprovisionnementForm(request.POST)
        # Limiter aux produits du commerçant
        form.fields['produit'].queryset = Produit.objects.filter(
            commercant=request.user.commercant
        )
        if form.is_valid():
            appro = form.save(commit=False)
            appro.commercant = request.user.commercant
            appro.save()  # save() décrémente le stock automatiquement
            messages.success(
                request,
                f"✓ Approvisionnement enregistré : +{appro.quantite} '{appro.produit.nom}'."
            )
            return redirect('produits:gestion_stock')
    else:
        form = ApprovisionnementForm()
        form.fields['produit'].queryset = Produit.objects.filter(
            commercant=request.user.commercant
        )

    return render(request, 'produits/ajouter_approvisionnement.html', {'form': form})


# ── OFFRES ────────────────────────────────────────────────────────────────────
@commercant_required
def gestion_offres(request):
    commercant = request.user.commercant
    produits_avec_offre = Produit.objects.filter(
        commercant=commercant, offre__isnull=False
    ).select_related('offre')
    produits_sans_offre = Produit.objects.filter(
        commercant=commercant, statut='actif', offre__isnull=True
    )

    return render(request, 'produits/gestion_offres.html', {
        'produits_avec_offre': produits_avec_offre,
        'produits_sans_offre': produits_sans_offre,
    })


@commercant_required
def ajouter_offre(request, produit_id):
    produit = get_object_or_404(
        Produit, pk=produit_id, commercant=request.user.commercant
    )

    if hasattr(produit, 'offre'):
        messages.warning(request, "Ce produit a déjà une offre active.")
        return redirect('produits:gestion_offres')

    if request.method == 'POST':
        form = OffreProduitForm(request.POST)
        if form.is_valid():
            offre = form.save(commit=False)
            offre.produit = produit
            offre.save()
            messages.success(
                request,
                f"✓ Offre '{offre.titre}' créée pour '{produit.nom}'."
            )
            return redirect('produits:gestion_offres')
    else:
        form = OffreProduitForm()

    return render(request, 'produits/ajouter_offre.html', {
        'form': form, 'produit': produit
    })


@commercant_required
def supprimer_offre(request, pk):
    offre = get_object_or_404(
        OffreProduit, pk=pk,
        produit__commercant=request.user.commercant
    )
    nom = offre.titre
    offre.delete()
    messages.info(request, f"Offre '{nom}' supprimée.")
    return redirect('produits:gestion_offres')


# ── DÉPENSES ──────────────────────────────────────────────────────────────────
@commercant_required
def gestion_depenses(request):
    commercant = request.user.commercant
    depenses = Depense.objects.filter(
        commercant=commercant
    ).order_by('-date')

    total = sum(d.montant for d in depenses)
    return render(request, 'produits/gestion_depenses.html', {
        'depenses': depenses,
        'total': total,
    })


@commercant_required
def ajouter_depense(request):
    if request.method == 'POST':
        form = DepenseForm(request.POST)
        if form.is_valid():
            depense = form.save(commit=False)
            depense.commercant = request.user.commercant
            depense.save()
            messages.success(
                request,
                f"✓ Dépense de {depense.montant} FCFA enregistrée."
            )
            return redirect('produits:gestion_depenses')
    else:
        form = DepenseForm()

    return render(request, 'produits/ajouter_depense.html', {'form': form})

# ── Favoris (liste de souhaits client) ──────────────────────────────────────

@login_required
def toggle_favori(request, pk):
    """Ajoute/retire un produit des favoris. Réponse JSON pour l'appel AJAX."""
    if not hasattr(request.user, 'client'):
        return JsonResponse({'error': "Réservé aux clients."}, status=403)

    produit = get_object_or_404(Produit, pk=pk)
    favori = Favori.objects.filter(client=request.user.client, produit=produit)

    if favori.exists():
        favori.delete()
        est_favori = False
    else:
        Favori.objects.create(client=request.user.client, produit=produit)
        est_favori = True

    return JsonResponse({'est_favori': est_favori})


@login_required
def mes_favoris(request):
    if not hasattr(request.user, 'client'):
        messages.error(request, "Réservé aux clients.")
        return redirect('home')

    favoris = Favori.objects.filter(
        client=request.user.client
    ).select_related('produit').prefetch_related('produit__images')

    return render(request, 'produits/mes_favoris.html', {'favoris': favoris})