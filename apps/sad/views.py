import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.db.models.functions import TruncDay

from apps.produits.models import Produit
from apps.commandes.models import LignePanier
from apps.evenements.models import EvenementSAD
from apps.users.views import admin_required
from .models import ConfigurationClimatique
from .forms import ConfigurationClimatiqueForm
from .utils import (
    calculer_marge_nette, identifier_top_produits, identifier_stocks_dormants,
    get_saison_actuelle, repartition_geographique_commandes,
    generer_notifications_stock, generer_notifications_evenements,
    generer_alerte_saison,
    suggerer_reapprovisionnement,
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
    generer_alerte_saison(commercant)

    produits = Produit.objects.filter(commercant=commercant, statut='actif')

    # Ventes confirmées (commandes en préparation ou livrées) des 30 derniers
    # jours. Le chiffre d'affaires et la marge nette partent de la MÊME base,
    # pour que « marge = ventes − coûts » soit toujours vrai à l'écran.
    depuis = timezone.now() - timedelta(days=30)
    lignes_vendues = LignePanier.objects.filter(
        produit__commercant=commercant,
        commande__isnull=False,
        commande__statut__in=['en_preparation', 'livree'],
        commande__date_commande__gte=depuis,
    ).select_related('produit')

    chiffre_affaires = cout_achat = frais_emballage = 0
    commandes_vendues = set()
    for ligne in lignes_vendues:
        chiffre_affaires += ligne.sous_total()
        cout_achat += ligne.produit.prix_achat * ligne.quantite
        frais_emballage += ligne.produit.frais_packaging * ligne.quantite
        commandes_vendues.add(ligne.commande_id)

    # Marge nette réelle = ventes − prix d'achat − frais d'emballage
    marge_totale = chiffre_affaires - cout_achat - frais_emballage
    nb_ventes = len(commandes_vendues)
    panier_moyen = chiffre_affaires / nb_ventes if nb_ventes else 0
    taux_marge = marge_totale / chiffre_affaires * 100 if chiffre_affaires else 0

    top_produits = identifier_top_produits(commercant)
    stocks_dormants = identifier_stocks_dormants(commercant)
    produits_alerte = [p for p in produits if p.est_en_alerte()]
    suggestions_reappro = suggerer_reapprovisionnement(commercant)

    evenements_proches = [e for e in EvenementSAD.objects.all() if e.est_proche()]
    saison = get_saison_actuelle()

    repartition_geo = repartition_geographique_commandes(commercant)

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
        'cout_achat': cout_achat,
        'frais_emballage': frais_emballage,
        'nb_ventes': nb_ventes,
        'panier_moyen': panier_moyen,
        'taux_marge': taux_marge,
        'marge_totale': marge_totale,
        'top_produits': top_produits,
        'stocks_dormants': stocks_dormants,
        'produits_alerte': produits_alerte,
        'suggestions_reappro': suggestions_reappro,
        'evenements_proches': evenements_proches,
        'saison': saison,
        'ventes_par_jour_json': json.dumps(ventes_par_jour, cls=DjangoJSONEncoder),
        'repartition_geo': repartition_geo,
        'repartition_geo_json': json.dumps(
            [
                {'region': ligne['region'], 'nb_commandes': ligne['nb_commandes']}
                for ligne in repartition_geo
            ],
            cls=DjangoJSONEncoder,
        ),
    })


@login_required
def stocks_dormants_liste(request):
    commercant = _commercant_required(request)
    if not commercant:
        return HttpResponseForbidden("Réservé aux commerçants.")

    stocks_dormants = identifier_stocks_dormants(commercant)

    return render(request, 'sad/stocks_dormants_liste.html', {
        'stocks_dormants': stocks_dormants,
    })


# ── Configuration climatique (§5.3.2 : paramétrable par l'administrateur) ──

@admin_required
def liste_climats(request):
    climats = ConfigurationClimatique.objects.all()
    return render(request, 'sad/liste_climats.html', {'climats': climats})


@admin_required
def creer_climat(request):
    if request.method == 'POST':
        form = ConfigurationClimatiqueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✓ Saison climatique ajoutée.")
            return redirect('sad:liste_climats')
    else:
        form = ConfigurationClimatiqueForm()
    return render(request, 'sad/form_climat.html', {
        'form': form, 'titre': "Ajouter une saison climatique",
    })


@admin_required
def modifier_climat(request, pk):
    climat = get_object_or_404(ConfigurationClimatique, pk=pk)
    if request.method == 'POST':
        form = ConfigurationClimatiqueForm(request.POST, instance=climat)
        if form.is_valid():
            form.save()
            messages.success(request, "✓ Saison climatique mise à jour.")
            return redirect('sad:liste_climats')
    else:
        form = ConfigurationClimatiqueForm(instance=climat)
    return render(request, 'sad/form_climat.html', {
        'form': form, 'titre': f"Modifier « {climat.nom} »",
    })


@admin_required
def supprimer_climat(request, pk):
    climat = get_object_or_404(ConfigurationClimatique, pk=pk)
    if request.method == 'POST':
        nom = climat.nom
        climat.delete()
        messages.success(request, f"✓ « {nom} » a été supprimée.")
        return redirect('sad:liste_climats')
    return render(request, 'sad/confirmer_suppression_climat.html', {
        'climat': climat,
    })
