from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages

from .models import Facture
from apps.commandes.models import Commande
from .services import generer_pdf_facture, envoyer_email_facture


def _commercant_required(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'commercant'):
        return None
    return request.user.commercant


@login_required
def generer_facture(request, commande_pk):
    commercant = _commercant_required(request)
    if not commercant:
        return HttpResponse("Réservé aux commerçants.", status=403)

    commande = get_object_or_404(
        Commande.objects.distinct(), pk=commande_pk, lignes__produit__commercant=commercant
    )

    facture = generer_pdf_facture(commande, commercant)
    return redirect('facturation:apercu_facture', pk=facture.pk)


@login_required
def apercu_facture(request, pk):
    commercant = _commercant_required(request)
    if not commercant:
        return HttpResponse("Réservé aux commerçants.", status=403)

    facture = get_object_or_404(
        Facture, pk=pk, commande__lignes__produit__commercant=commercant
    )
    return render(request, 'facturation/apercu_facture.html', {'facture': facture})


@login_required
def telecharger_facture(request, pk):
    commercant = _commercant_required(request)
    if not commercant:
        return HttpResponse("Réservé aux commerçants.", status=403)

    facture = get_object_or_404(
        Facture, pk=pk, commande__lignes__produit__commercant=commercant
    )
    if facture.pdf_url:
        response = HttpResponse(facture.pdf_url.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="facture_{facture.commande.id}.pdf"'
        return response
    return HttpResponse("Facture non générée.", status=404)


@login_required
def envoyer_facture_email(request, pk):
    commercant = _commercant_required(request)
    if not commercant:
        return HttpResponse("Réservé aux commerçants.", status=403)

    facture = get_object_or_404(
        Facture, pk=pk, commande__lignes__produit__commercant=commercant
    )
    if envoyer_email_facture(facture):
        messages.success(request, "✓ Facture envoyée au client par email.")
    else:
        messages.error(
            request,
            "Impossible d'envoyer la facture (email client manquant ou "
            "erreur d'envoi)."
        )

    return redirect('facturation:apercu_facture', pk=facture.pk)