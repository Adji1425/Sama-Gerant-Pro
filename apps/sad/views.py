import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.db.models.functions import TruncDay

from apps.produits.models import Produit
from apps.commandes.models import LignePanier
from apps.evenements.models import EvenementSAD
from apps.notifications.models import Notification
from .utils import (
    calculer_marge_nette, identifier_top_produits, identifier_stocks_dormants,
    get_saison_actuelle, SAISONS_SENEGAL,
    generer_notifications_stock, generer_notifications_evenements,
)


def _commercant_required(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'commercant'):
        return None
    return request.user.commercant


@login_required
def dashboard(request):
    commercant = _commercant_required(request)
    if not commercant:
        return HttpResponseForbidden("Réservé aux commerçants.")

    # Génère les notifications avant d'afficher le tableau de bord
    generer_notifications_stock(commercant)
    generer_notifications_evenements(commercant)

    produits = Produit.objects.filter(commercant=commercant, statut='actif')

    # ✅ CORRIGÉ : LignePanier au lieu de DetailsCommande
    # commande__isnull=False -> uniquement les lignes rattachées à une vraie commande (pas le panier en cours)
    lignes_vendues = LignePanier.objects.filter(
        produit__commercant=commercant,
        commande__isnull=False,
        commande__statut__in=['en_preparation', 'livree'],
    )
    chiffre_affaires = sum(ligne.sous_total() for ligne in lignes_vendues)
    marge_totale = sum(calculer_marge_nette(p) for p in produits)

    top_produits = identifier_top_produits(commercant)
    stocks_dormants = identifier_stocks_dormants(commercant)
    produits_alerte = [p for p in produits if p.est_en_alerte()]

    evenements_proches = [e for e in EvenementSAD.objects.all() if e.est_proche()]
    saison = get_saison_actuelle()

    notifications = Notification.objects.filter(commercant=commercant, lu=False)[:10]

    date_limite = timezone.now() - timedelta(days=30)
    ventes_par_jour = list(
        LignePanier.objects
        .filter(
            produit__commercant=commercant,
            commande__isnull=False,
            commande__date_commande__gte=date_limite,
        )
        .annotate(jour=TruncDay('commande__date_commande'))
        .values('jour')
        .annotate(total=Sum('quantite'))
        .order_by('jour')
    )

    return render(request, 'sad/dashboard.html', {
        'chiffre_affaires': chiffre_affaires,
        'marge_totale': marge_totale,
        'top_produits': top_produits,
        'stocks_dormants': stocks_dormants,
        'produits_alerte': produits_alerte,
        'evenements_proches': evenements_proches,
        'saison': saison,
        'saisons_labels': SAISONS_SENEGAL,
        'notifications': notifications,
        'ventes_par_jour_json': json.dumps(ventes_par_jour, cls=DjangoJSONEncoder),
    })


@login_required
def marquer_notification_lue(request, pk):
    commercant = _commercant_required(request)
    if not commercant:
        return HttpResponseForbidden("Réservé aux commerçants.")

    Notification.objects.filter(pk=pk, commercant=commercant).update(lu=True)
    return redirect('sad:dashboard')
