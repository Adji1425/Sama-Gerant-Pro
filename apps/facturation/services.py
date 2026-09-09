"""
Fonctions de service pour la facturation, réutilisées :
- par les vues manuelles (apps/facturation/views.py)
- par le déclenchement automatique quand une commande passe à 'livree'
  (apps/commandes/views.py -> changer_statut)
"""
import io
import logging

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from xhtml2pdf import pisa

from .models import Facture

logger = logging.getLogger(__name__)


def generer_pdf_facture(commande, commercant):
    """
    Génère (ou régénère) le PDF de la facture pour une commande donnée
    et l'enregistre sur le modèle Facture. Retourne l'objet Facture.
    """
    facture, _ = Facture.objects.get_or_create(commande=commande)

    html = render_to_string('facturation/facture_pdf.html', {
        'commande': commande, 'facture': facture, 'commercant': commercant,
    })

    buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=buffer)
    buffer.seek(0)

    facture.pdf_url.save(f"facture_{commande.id}.pdf", buffer, save=True)
    return facture


def envoyer_email_facture(facture):
    """
    Envoie la facture PDF par email au client, en pièce jointe, avec un
    email HTML soigné (+ repli texte brut pour les clients mail qui ne
    supportent pas le HTML). Ne fait rien si la facture n'a pas de PDF
    ou si le client n'a pas d'email renseigné. N'échoue jamais
    bruyamment (utilisé aussi en tâche automatique) : les erreurs SMTP
    sont journalisées, pas levées.
    """
    client = facture.commande.client
    client_email = getattr(client.utilisateur, 'email', None)
    if not (facture.pdf_url and client_email):
        return False

    commercant = facture.commande.lignes.select_related(
        'produit__commercant'
    ).first()
    commercant = commercant.produit.commercant if commercant and commercant.produit else None
    if commercant is None:
        return False

    contexte = {
        'commande': facture.commande,
        'facture': facture,
        'commercant': commercant,
        'client_prenom': client.utilisateur.first_name or client.utilisateur.username,
    }

    texte_brut = (
        f"Bonjour {contexte['client_prenom']},\n\n"
        f"Votre commande #{facture.commande.id} a bien été livrée. "
        f"Merci pour votre confiance !\n\n"
        f"Montant total : {facture.commande.montant_total:.0f} FCFA\n\n"
        f"Vous trouverez votre facture détaillée en pièce jointe.\n\n"
        f"— {commercant.nom_boutique}, via Sama-Gérant Pro"
    )
    html_body = render_to_string('facturation/email_facture.html', contexte)

    try:
        email = EmailMultiAlternatives(
            subject=f"Votre facture — Commande #{facture.commande.id} chez {commercant.nom_boutique}",
            body=texte_brut,
            from_email=settings.EMAIL_HOST_USER or None,
            to=[client_email],
        )
        email.attach_alternative(html_body, "text/html")
        email.attach_file(facture.pdf_url.path)
        email.send(fail_silently=False)
        return True
    except Exception:
        logger.exception(
            "Échec de l'envoi automatique de la facture #%s", facture.pk
        )
        return False


def generer_et_envoyer_facture(commande, commercant):
    """Raccourci : génère le PDF puis envoie l'email au client."""
    facture = generer_pdf_facture(commande, commercant)
    envoyer_email_facture(facture)
    return facture