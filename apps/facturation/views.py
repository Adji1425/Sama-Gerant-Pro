import io

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from xhtml2pdf import pisa

from .models import Facture
from apps.commandes.models import Commande


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

    facture, _ = Facture.objects.get_or_create(commande=commande)

    html = render_to_string('facturation/facture_pdf.html', {
        'commande': commande, 'facture': facture, 'commercant': commercant,
    })

    buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=buffer)
    buffer.seek(0)

    facture.pdf_url.save(f"facture_{commande.id}.pdf", buffer, save=True)
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
    client_email = facture.commande.client.utilisateur.email

    if facture.pdf_url and client_email:
        email = EmailMessage(
            subject=f"Votre facture - Commande #{facture.commande.id}",
            body="Merci pour votre commande ! Veuillez trouver votre facture en pièce jointe.",
            from_email=settings.EMAIL_HOST_USER,
            to=[client_email],
        )
        email.attach_file(facture.pdf_url.path)
        email.send()

    return redirect('facturation:apercu_facture', pk=facture.pk)
