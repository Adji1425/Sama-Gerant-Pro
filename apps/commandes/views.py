from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Panier, LignePanier, Commande, DetailsCommande
from apps.produits.models import Produit


# ── HELPERS ──────────────────────────────────────────────────────────────────

def get_or_create_panier(client):
    """Récupère ou crée le panier du client"""
    panier, _ = Panier.objects.get_or_create(client=client)
    return panier


# ── PANIER ───────────────────────────────────────────────────────────────────

@login_required
def voir_panier(request):
    """Affiche le panier du client connecté"""
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    panier = get_or_create_panier(request.user.client)
    lignes = panier.lignes.select_related('produit').all()

    context = {
        'panier': panier,
        'lignes': lignes,
        'total': panier.total(),
        'nombre_articles': panier.nombre_articles(),
    }
    return render(request, 'commandes/panier.html', context)


@login_required
def ajouter_panier(request, produit_id):
    """Ajoute un produit au panier"""
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    if request.method == 'POST':
        produit = get_object_or_404(Produit, pk=produit_id, statut='actif')
        quantite = int(request.POST.get('quantite', 1))

        # Vérifier le stock disponible
        if quantite > produit.quantite:
            messages.error(
                request,
                f"Stock insuffisant. Seulement "
                f"{produit.quantite} unité(s) disponible(s)."
            )
            return redirect('produits:fiche_produit', pk=produit_id)

        panier = get_or_create_panier(request.user.client)

        # Si le produit est déjà dans le panier → augmenter la quantité
        ligne_existante = panier.lignes.filter(produit=produit).first()
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
                prix_unitaire_snapshot=produit.prix_vente,
            )

        messages.success(
            request,
            f"✓ {produit.nom} ajouté au panier !"
        )
        return redirect('produits:fiche_produit', pk=produit_id)

    return redirect('produits:catalogue')


@login_required
def modifier_panier(request, ligne_id):
    """Modifie la quantité d'une ligne du panier"""
    ligne = get_object_or_404(
        LignePanier,
        pk=ligne_id,
        panier__client=request.user.client
    )

    if request.method == 'POST':
        quantite = int(request.POST.get('quantite', 1))

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
    """Supprime un article du panier"""
    ligne = get_object_or_404(
        LignePanier,
        pk=ligne_id,
        panier__client=request.user.client
    )
    nom_produit = ligne.produit.nom
    ligne.delete()
    messages.info(request, f"{nom_produit} retiré du panier.")
    return redirect('commandes:voir_panier')


# ── COMMANDE ─────────────────────────────────────────────────────────────────

@login_required
def valider_commande(request):
    """
    Valide le panier et crée la commande.
    Copie LignePanier → DetailsCommande.
    Décrémente le stock.
    Vide le panier.
    """
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    client = request.user.client
    panier = get_or_create_panier(client)
    lignes = panier.lignes.all()

    if not lignes.exists():
        messages.error(request, "Votre panier est vide.")
        return redirect('commandes:voir_panier')

    if request.method == 'POST':
        adresse = request.POST.get(
            'adresse_livraison',
            client.adresse_livraison
        )
        telephone = request.POST.get(
            'telephone',
            request.user.telephone
        )

        if not adresse or not telephone:
            messages.error(
                request,
                "Veuillez renseigner l'adresse et le téléphone."
            )
            return redirect('commandes:voir_panier')

        # Vérification finale des stocks
        for ligne in lignes:
            if ligne.quantite > ligne.produit.quantite:
                messages.error(
                    request,
                    f"Stock insuffisant pour {ligne.produit.nom}. "
                    f"Seulement {ligne.produit.quantite} disponible(s)."
                )
                return redirect('commandes:voir_panier')

        # Créer la commande
        commande = Commande.objects.create(
            client=client,
            adresse_livraison_reel=adresse,
            telephone=telephone,
            statut='en_attente',
        )

        # Copier chaque LignePanier → DetailsCommande
        for ligne in lignes:
            # Vérifier si une offre est active
            offre_active = None
            if hasattr(ligne.produit, 'offre'):
                if ligne.produit.offre.est_active():
                    offre_active = ligne.produit.offre

            DetailsCommande.objects.create(
                commande=commande,
                produit=ligne.produit,
                offre=offre_active,
                quantite=ligne.quantite,
                prix_unitaire_vente=ligne.prix_unitaire_snapshot,
            )

            # Décrémenter le stock
            ligne.produit.quantite -= ligne.quantite
            ligne.produit.save()

        # Calculer le montant total
        commande.calculer_montant()

        # Vider le panier
        panier.vider()

        # Générer une notification pour le commerçant
        _notifier_commercant(commande)

        messages.success(
            request,
            f"✓ Commande #{commande.id} passée avec succès !"
        )
        return redirect('commandes:confirmation', commande_id=commande.id)

    # GET — page récapitulatif avant validation
    context = {
        'panier': panier,
        'lignes': lignes,
        'total': panier.total(),
        'client': client,
    }
    return render(request, 'commandes/recap_commande.html', context)


def _notifier_commercant(commande):
    """Crée une notification pour le commerçant dès qu'une commande arrive"""
    try:
        from apps.notifications.models import Notification
        # Trouver le commerçant concerné
        produits = commande.details.select_related(
            'produit__commercant'
        ).all()
        commercants_notifies = set()
        for detail in produits:
            if detail.produit:
                commercant = detail.produit.commercant
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
        pass  # Ne pas bloquer si la notification échoue


@login_required
def confirmation(request, commande_id):
    """Page de confirmation après validation de la commande"""
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )
    context = {'commande': commande}
    return render(request, 'commandes/confirmation.html', context)


@login_required
def mes_commandes(request):
    """Historique des commandes du client"""
    if not hasattr(request.user, 'client'):
        return redirect('home')

    commandes = Commande.objects.filter(
        client=request.user.client
    ).prefetch_related('details__produit')

    context = {'commandes': commandes}
    return render(request, 'commandes/mes_commandes.html', context)


@login_required
def detail_commande(request, commande_id):
    """Détail d'une commande spécifique"""
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )
    details = commande.details.select_related('produit', 'offre').all()
    context = {
        'commande': commande,
        'details': details,
    }
    return render(request, 'commandes/detail_commande.html', context)