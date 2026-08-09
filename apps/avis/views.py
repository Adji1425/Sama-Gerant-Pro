from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from .models import Avis
from .forms import AvisForm
from apps.commandes.models import LignePanier
from apps.produits.models import Produit


def _client_required(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'client'):
        return None
    return request.user.client


@login_required
def ajouter_avis(request, produit_pk):
    client = _client_required(request)
    if not client:
        return HttpResponseForbidden("Réservé aux clients.")

    produit = get_object_or_404(Produit, pk=produit_pk)

    # ✅ CORRIGÉ : vérifie l'achat réel via LignePanier (au lieu de DetailsCommande)
    # commande__isnull=False -> uniquement une ligne rattachée à une vraie commande, pas le panier en cours
    ligne_commande = LignePanier.objects.filter(
        produit=produit,
        commande__isnull=False,
        commande__client=client,
        commande__statut='livree',
    ).first()

    if not ligne_commande:
        messages.error(request, "Vous devez avoir acheté et reçu ce produit pour laisser un avis.")
        return redirect('produits:fiche_produit', pk=produit.pk)

    if Avis.objects.filter(client=client, produit=produit).exists():
        messages.info(request, "Vous avez déjà laissé un avis sur ce produit.")
        return redirect('produits:fiche_produit', pk=produit.pk)

    if request.method == 'POST':
        form = AvisForm(request.POST)
        if form.is_valid():
            avis = form.save(commit=False)
            avis.client = client
            avis.produit = produit
            avis.ligne_commande = ligne_commande
            avis.verifie_achat = True
            avis.save()
            messages.success(request, "Merci pour votre avis !")
            return redirect('produits:fiche_produit', pk=produit.pk)
    else:
        form = AvisForm()

    return render(request, 'avis/form_avis.html', {'form': form, 'produit': produit})


@login_required
def modifier_avis(request, pk):
    client = _client_required(request)
    if not client:
        return HttpResponseForbidden("Réservé aux clients.")

    avis = get_object_or_404(Avis, pk=pk, client=client)
    if request.method == 'POST':
        form = AvisForm(request.POST, instance=avis)
        if form.is_valid():
            form.save()
            messages.success(request, "Avis modifié.")
            return redirect('produits:fiche_produit', pk=avis.produit.pk)
    else:
        form = AvisForm(instance=avis)

    return render(request, 'avis/form_avis.html', {'form': form, 'produit': avis.produit})


@login_required
def supprimer_avis(request, pk):
    client = _client_required(request)
    if not client:
        return HttpResponseForbidden("Réservé aux clients.")

    avis = get_object_or_404(Avis, pk=pk, client=client)
    produit_pk = avis.produit.pk
    avis.delete()
    messages.info(request, "Avis supprimé.")
    return redirect('produits:fiche_produit', pk=produit_pk)


def liste_avis_produit(request, produit_pk):
    produit = get_object_or_404(Produit, pk=produit_pk)
    avis = produit.avis_set.all().order_by('-date_avis')
    return render(request, 'avis/liste_avis.html', {'produit': produit, 'avis': avis})
