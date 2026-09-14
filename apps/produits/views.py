from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import Produit, Categorie, ImageProd, Depense, Approvisionnement, Favori
from .forms import ProduitForm, ProduitModifierForm, DepenseForm, ApprovisionnementForm
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
        'est_favori': est_favori,
    })


# ── GESTION PRODUITS (Commerçant) ─────────────────────────────────────────────
@commercant_required
def gestion_produits(request):
    commercant = request.user.commercant
    produits = Produit.objects.filter(
        commercant=commercant
    ).exclude(
        statut='supprime'
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
        form = ProduitModifierForm(request.POST, instance=produit)
        if form.is_valid():
            form.save()

            # Nouvelles images
            nouvelles_images = request.FILES.getlist('images')
            for img in nouvelles_images:
                ImageProd.objects.create(produit=produit, image=img)

            messages.success(request, "✓ Produit modifié avec succès !")
            return redirect('produits:gestion_produits')
    else:
        form = ProduitModifierForm(instance=produit)

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


@commercant_required
def supprimer_produit(request, pk):
    """
    Suppression "douce" d'un produit archivé (§5.2.1 du cahier des
    charges) : le produit passe au statut 'supprime' et disparaît de
    tous les listings (catalogue, actifs, archivés), mais la ligne
    reste en base. Les commandes/factures passées qui le référencent
    restent donc intactes, et les statistiques historiques du SAD ne
    sont pas faussées. Uniquement disponible depuis l'onglet "Archivés"
    (on ne supprime jamais un produit encore en vente).
    """
    produit = get_object_or_404(
        Produit, pk=pk, commercant=request.user.commercant, statut='archive'
    )
    produit.statut = 'supprime'
    produit.save()
    messages.success(request, f"'{produit.nom}' a été supprimé du catalogue.")
    return redirect('produits:gestion_produits')


# ── STOCK ─────────────────────────────────────────────────────────────────────
@commercant_required
def gestion_stock(request):
    commercant = request.user.commercant
    tous_produits = Produit.objects.filter(
        commercant=commercant, statut='actif'
    ).order_by('quantite')

    # KPI calculés avant filtrage
    total_produits = tous_produits.count()
    en_alerte = [p for p in tous_produits if p.est_en_alerte()]

    produits = tous_produits

    # Recherche par nom, comme dans "Mes produits"
    recherche = request.GET.get('q', '').strip()
    if recherche:
        produits = produits.filter(nom__icontains=recherche)

    # Filtre par état (pastilles : Tous / En alerte / OK)
    etat_filtre = request.GET.get('etat', '')
    if etat_filtre == 'alerte':
        produits = [p for p in produits if p.est_en_alerte()]
    elif etat_filtre == 'ok':
        produits = [p for p in produits if not p.est_en_alerte()]

    return render(request, 'produits/gestion_stock.html', {
        'produits': produits,
        'total_produits': total_produits,
        'en_alerte': en_alerte,
        'recherche': recherche,
        'etat_filtre': etat_filtre,
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


# ── DÉPENSES ──────────────────────────────────────────────────────────────────
@commercant_required
def gestion_depenses(request):
    import calendar
    from datetime import date

    commercant = request.user.commercant
    toutes_depenses = Depense.objects.filter(commercant=commercant).order_by('-date')

    # KPI calculés avant filtrage
    total = sum(d.montant for d in toutes_depenses)
    nb_depenses = toutes_depenses.count()

    depenses = toutes_depenses

    # Recherche par type ou description, comme dans "Mes produits"
    recherche = request.GET.get('q', '').strip()
    if recherche:
        depenses = depenses.filter(
            Q(type__icontains=recherche) | Q(description__icontains=recherche)
        )

    # ── Vue calendrier (façon Wave) : dépenses du mois affichées jour par
    # jour, pour repérer d'un coup d'œil les périodes d'achat/réappro. ──
    aujourdhui = date.today()
    try:
        mois = int(request.GET.get('mois', aujourdhui.month))
        annee = int(request.GET.get('annee', aujourdhui.year))
        date(annee, mois, 1)  # valide la combinaison mois/année
    except (ValueError, TypeError):
        mois, annee = aujourdhui.month, aujourdhui.year

    depenses_du_mois = Depense.objects.filter(
        commercant=commercant, date__year=annee, date__month=mois
    )
    depenses_par_jour = {}
    for d in depenses_du_mois:
        depenses_par_jour.setdefault(d.date.day, []).append(d)

    cal = calendar.Calendar(firstweekday=0)  # semaine commence lundi
    calendrier_semaines = []
    for semaine in cal.monthdayscalendar(annee, mois):
        jours_semaine = []
        for jour in semaine:
            if jour == 0:
                jours_semaine.append(None)
            else:
                depenses_jour = depenses_par_jour.get(jour, [])
                jours_semaine.append({
                    'jour': jour,
                    'depenses': depenses_jour,
                    'total_jour': sum(d.montant for d in depenses_jour),
                    'est_aujourdhui': (
                        jour == aujourdhui.day
                        and mois == aujourdhui.month
                        and annee == aujourdhui.year
                    ),
                })
        calendrier_semaines.append(jours_semaine)

    mois_precedent = mois - 1 if mois > 1 else 12
    annee_mois_precedent = annee if mois > 1 else annee - 1
    mois_suivant = mois + 1 if mois < 12 else 1
    annee_mois_suivant = annee if mois < 12 else annee + 1

    noms_mois = [
        '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet',
        'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
    ]

    return render(request, 'produits/gestion_depenses.html', {
        'depenses': depenses,
        'total': total,
        'nb_depenses': nb_depenses,
        'recherche': recherche,
        'vue': request.GET.get('vue', 'calendrier'),
        'calendrier_semaines': calendrier_semaines,
        'mois_actuel': mois,
        'annee_actuelle': annee,
        'nom_mois_actuel': noms_mois[mois],
        'mois_precedent': mois_precedent,
        'annee_mois_precedent': annee_mois_precedent,
        'mois_suivant': mois_suivant,
        'annee_mois_suivant': annee_mois_suivant,
        'total_mois': sum(d.montant for d in depenses_du_mois),
        'est_mois_courant': (mois == aujourdhui.month and annee == aujourdhui.year),
        'aujourdhui': aujourdhui,
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