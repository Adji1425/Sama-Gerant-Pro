"""
Fonctions de service pour la facturation, réutilisées :
- par les vues manuelles (apps/facturation/views.py)
- par le déclenchement automatique quand une commande passe à 'livree'
  (apps/commandes/views.py -> changer_statut)
"""
import io
import logging

from django.template.loader import render_to_string
from django.core.mail import EmailMessage
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
    Envoie la facture PDF par email au client, en pièce jointe.
    Ne fait rien si la facture n'a pas de PDF ou si le client n'a pas
    d'email renseigné. N'échoue jamais bruyamment (utilisé aussi en
    tâche automatique) : les erreurs SMTP sont journalisées, pas levées.
    """
    client_email = getattr(facture.commande.client.utilisateur, 'email', None)
    if not (facture.pdf_url and client_email):
        return False

    try:
        email = EmailMessage(
            subject=f"Votre facture - Commande #{facture.commande.id}",
            body=(
                "Bonjour,\n\n"
                "Votre commande a été livrée. Veuillez trouver ci-joint "
                "votre facture.\n\nMerci de votre confiance !"
            ),
            from_email=settings.EMAIL_HOST_USER or None,
            to=[client_email],
        )
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