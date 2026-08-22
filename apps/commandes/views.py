from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Panier, LignePanier, Commande
from apps.produits.models import Produit
from django.http import JsonResponse
from apps.facturation.models import Facture


# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_or_create_panier(client):
    panier, _ = Panier.objects.get_or_create(client=client)
    return panier


# ── PANIER ────────────────────────────────────────────────────────────────────
@login_required
def voir_panier(request):
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    panier = get_or_create_panier(request.user.client)
    lignes = panier.lignes.filter(
        commande=None
    ).select_related('produit').all()

    context = {
        'panier': panier,
        'lignes': lignes,
        'total': sum(l.sous_total() for l in lignes),
        'nombre_articles': sum(l.quantite for l in lignes),
    }
    return render(request, 'commandes/panier.html', context)


@login_required
def ajouter_panier(request, produit_id):
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    if request.method == 'POST':
        produit = get_object_or_404(Produit, pk=produit_id, statut='actif')

        try:
            quantite = int(request.POST.get('quantite', 1))
        except (TypeError, ValueError):
            messages.error(request, "Quantité invalide.")
            return redirect('produits:fiche_produit', pk=produit_id)

        if quantite < 1:
            messages.error(request, "La quantité doit être d'au moins 1.")
            return redirect('produits:fiche_produit', pk=produit_id)

        if quantite > produit.quantite:
            messages.error(
                request,
                f"Stock insuffisant. Seulement "
                f"{produit.quantite} unité(s) disponible(s)."
            )
            return redirect('produits:fiche_produit', pk=produit_id)

        panier = get_or_create_panier(request.user.client)

        # ✅ Chercher ligne existante sans commande (dans le panier actif)
        ligne_existante = panier.lignes.filter(
            produit=produit, commande=None
        ).first()

        if ligne_existante:
            nouvelle_qte = ligne_existante.quantite + quantite
            if nouvelle_qte > produit.quantite:
                messages.error(
                    request,
                    f"Vous avez déjà {ligne_existante.quantite} de ce "
                    f"produit dans votre panier."
                )
                return redirect('produits:fiche_produit', pk=produit_id)
            ligne_existante.quantite = nouvelle_qte
            ligne_existante.save()
        else:
            LignePanier.objects.create(
                panier=panier,
                produit=produit,
                quantite=quantite,
                # ✅ CORRIGÉ : prix_unitaire_vente
                prix_unitaire_vente=produit.prix_vente,
            )

        messages.success(request, f"✓ {produit.nom} ajouté au panier !")
        return redirect('produits:fiche_produit', pk=produit_id)

    return redirect('produits:catalogue')


@login_required
def modifier_panier(request, ligne_id):
    ligne = get_object_or_404(
        LignePanier,
        pk=ligne_id,
        panier__client=request.user.client,
        commande=None
    )

    if request.method == 'POST':
        try:
            quantite = int(request.POST.get('quantite', 1))
        except (TypeError, ValueError):
            messages.error(request, "Quantité invalide.")
            return redirect('commandes:voir_panier')

        if quantite < 1:
            ligne.delete()
            messages.info(request, "Article retiré du panier.")
        elif quantite > ligne.produit.quantite:
            messages.error(
                request,
                f"Stock insuffisant. Max : {ligne.produit.quantite}"
            )
        else:
            ligne.quantite = quantite
            ligne.save()
            messages.success(request, "Panier mis à jour.")

    return redirect('commandes:voir_panier')


@login_required
def supprimer_panier(request, ligne_id):
    ligne = get_object_or_404(
        LignePanier,
        pk=ligne_id,
        panier__client=request.user.client,
        commande=None
    )
    nom_produit = ligne.produit.nom
    ligne.delete()
    messages.info(request, f"{nom_produit} retiré du panier.")
    return redirect('commandes:voir_panier')


# ── COMMANDE ──────────────────────────────────────────────────────────────────
@login_required
def valider_commande(request):
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    client = request.user.client
    panier = get_or_create_panier(client)
    lignes = panier.lignes.filter(commande=None)

    if not lignes.exists():
        messages.error(request, "Votre panier est vide.")
        return redirect('commandes:voir_panier')

    if request.method == 'POST':
        adresse = request.POST.get('adresse_livraison', client.adresse_livraison)
        telephone = request.POST.get('telephone', request.user.telephone)

        if not adresse or not telephone:
            messages.error(
                request,
                "Veuillez renseigner l'adresse et le téléphone."
            )
            return redirect('commandes:voir_panier')

        for ligne in lignes:
            if ligne.produit and ligne.quantite > ligne.produit.quantite:
                messages.error(
                    request,
                    f"Stock insuffisant pour {ligne.produit.nom}."
                )
                return redirect('commandes:voir_panier')

        commande = Commande.objects.create(
            client=client,
            adresse_livraison_reel=adresse,
            telephone=telephone,
            statut='en_attente',
        )

        for ligne in lignes:
            offre_active = None
            if ligne.produit and hasattr(ligne.produit, 'offre'):
                try:
                    if ligne.produit.offre.est_active():
                        offre_active = ligne.produit.offre
                except Exception:
                    pass

            # ✅ Rattacher LignePanier à la commande
            ligne.commande = commande
            ligne.offre = offre_active
            ligne.save()

            # Décrémenter le stock
            if ligne.produit:
                ligne.produit.quantite -= ligne.quantite
                ligne.produit.save()

        commande.calculer_montant()
        _notifier_commercant(commande)

        messages.success(
            request,
            f"✓ Commande #{commande.id} passée avec succès !"
        )
        return redirect('commandes:confirmation', commande_id=commande.id)

    context = {
        'panier': panier,
        'lignes': lignes,
        'total': sum(l.sous_total() for l in lignes),
        'client': client,
    }
    return render(request, 'commandes/recap_commande.html', context)


def _notifier_commercant(commande):
    """Notification commerçant — utilise commande.lignes"""
    try:
        from apps.notifications.models import Notification
        # ✅ CORRIGÉ : commande.lignes au lieu de commande.details
        lignes = commande.lignes.select_related('produit__commercant').all()
        commercants_notifies = set()
        for ligne in lignes:
            if ligne.produit:
                commercant = ligne.produit.commercant
                if commercant.id not in commercants_notifies:
                    Notification.objects.create(
                        commercant=commercant,
                        titre=f"Nouvelle commande #{commande.id}",
                        message=(
                            f"Le client {commande.client} vient de passer "
                            f"une commande de {commande.montant_total:.0f} FCFA."
                        ),
                        type='commande',
                    )
                    commercants_notifies.add(commercant.id)
    except Exception:
        pass


@login_required
def confirmation(request, commande_id):
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )
    return render(request, 'commandes/confirmation.html', {'commande': commande})


@login_required
def mes_commandes(request):
    if not hasattr(request.user, 'client'):
        return redirect('home')

    commandes = Commande.objects.filter(
        client=request.user.client
    ).prefetch_related('lignes__produit')

    return render(request, 'commandes/mes_commandes.html', {'commandes': commandes})


@login_required
def detail_commande(request, commande_id):
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )
    # ✅ CORRIGÉ : commande.lignes
    details = commande.lignes.select_related('produit', 'offre').all()

    avis_par_produit = {}
    if commande.statut == 'livree':
        from apps.avis.models import Avis
        produit_ids = [d.produit_id for d in details if d.produit_id]
        avis_par_produit = {
            a.produit_id: a
            for a in Avis.objects.filter(client=commande.client, produit_id__in=produit_ids)
        }

    return render(request, 'commandes/detail_commande.html', {
        'commande': commande,
        'details': details,
        'avis_par_produit': avis_par_produit,
    })


@login_required
def get_statut_json(request, commande_id):
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )

    statuts_ordre = {
        'en_attente': 1,
        'en_preparation': 2,
        'livree': 3,
        'annulee': -1,
    }

    return JsonResponse({
        'statut': commande.statut,
        'statut_display': commande.get_statut_display(),
        'ordre': statuts_ordre.get(commande.statut, 0),
        'montant_total': commande.montant_total,
        'date_commande': commande.date_commande.strftime('%d/%m/%Y à %H:%M'),
    })



# Décorateur commerçant
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


@login_required
def commandes_commercant(request):
    """Liste des commandes reçues par le commerçant"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    commercant = request.user.commercant
    # Commandes contenant des produits de ce commerçant
    commandes = Commande.objects.filter(
        lignes__produit__commercant=commercant
    ).distinct().prefetch_related(
        'lignes__produit', 'client__utilisateur'
    ).order_by('-date_commande')

    # Filtrer par statut
    statut_filtre = request.GET.get('statut', '')
    if statut_filtre:
        commandes = commandes.filter(statut=statut_filtre)

    context = {
        'commandes': commandes,
        'statut_filtre': statut_filtre,
        'total_en_attente': Commande.objects.filter(
            lignes__produit__commercant=commercant,
            statut='en_attente'
        ).distinct().count(),
        'total_en_preparation': Commande.objects.filter(
            lignes__produit__commercant=commercant,
            statut='en_preparation'
        ).distinct().count(),
    }
    return render(request, 'commandes/commandes_commercant.html', context)


@login_required
def detail_commande_commercant(request, commande_id):
    """Détail d'une commande côté commerçant"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    commande = get_object_or_404(Commande, pk=commande_id)
    lignes = commande.lignes.filter(
        produit__commercant=request.user.commercant
    ).select_related('produit', 'offre')

    return render(request, 'commandes/detail_commande_commercant.html', {
        'commande': commande,
        'lignes': lignes,
    })


@login_required
def changer_statut(request, commande_id):
    """Changer le statut d'une commande"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    if request.method == 'POST':
        commande = get_object_or_404(Commande, pk=commande_id)
        nouveau_statut = request.POST.get('statut')

        statuts_valides = ['en_attente', 'en_preparation', 'livree', 'annulee']
        if nouveau_statut in statuts_valides:
            ancien_statut = commande.statut
            commande.statut = nouveau_statut
            commande.save()

            # Notifier le client
            try:
                from apps.notifications.models import Notification
                if hasattr(commande.client, 'utilisateur'):
                    pass  # notifications client à implémenter si besoin
            except Exception:
                pass

            # Générer facture si livrée
            if nouveau_statut == 'livree' and ancien_statut != 'livree':
                _generer_facture_auto(commande)

            messages.success(
                request,
                f"✓ Statut de la commande #{commande.id} → "
                f"{commande.get_statut_display()}"
            )

    return redirect('commandes:commandes_commercant')


def _generer_facture_auto(commande):
    """Génère automatiquement la facture quand commande livrée"""
    try:
        if not hasattr(commande, 'facture'):
            Facture.objects.create(commande=commande)
    except Exception:
        pass


@login_required
def generer_facture(request, commande_id):
    """Génère et affiche la facture PDF"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    commande = get_object_or_404(Commande, pk=commande_id)

    # Créer la facture si elle n'existe pas
    facture, created = Facture.objects.get_or_create(commande=commande)

    # Générer le PDF avec xhtml2pdf
    from django.template.loader import get_template
    from django.http import HttpResponse
    try:
        from xhtml2pdf import pisa
        template = get_template('facturation/facture_pdf.html')
        html = template.render({
            'commande': commande,
            'facture': facture,
            'lignes': commande.lignes.select_related('produit', 'offre').all(),
        })
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="facture_{commande.id}.pdf"'
        )
        pisa.CreatePDF(html, dest=response)
        return response
    except Exception as e:
        messages.error(request, f"Erreur génération PDF : {e}")
        return redirect('commandes:commandes_commercant')