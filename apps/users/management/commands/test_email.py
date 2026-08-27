from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    Envoie un email de test pour vérifier rapidement la configuration SMTP
    (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD dans .env), sans avoir à
    déclencher une vraie alerte stock ou facture.

    Usage :
        python manage.py test_email destinataire@example.com
    """
    help = "Envoie un email de test pour vérifier la configuration SMTP."

    def add_arguments(self, parser):
        parser.add_argument('destinataire', type=str)

    def handle(self, *args, **options):
        destinataire = options['destinataire']

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError(
                "EMAIL_HOST_USER et/ou EMAIL_HOST_PASSWORD ne sont pas "
                "renseignés dans le fichier .env. Voir les commentaires "
                "dans .env pour générer un mot de passe d'application Gmail."
            )

        self.stdout.write(f"Envoi vers {destinataire} via {settings.EMAIL_HOST}...")

        send_mail(
            subject="[Sama-Gérant Pro] Test de configuration email",
            message=(
                "Si vous recevez cet email, la configuration SMTP de "
                "Sama-Gérant Pro fonctionne correctement."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinataire],
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS("✓ Email envoyé sans erreur."))
