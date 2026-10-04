from django.core.management.base import BaseCommand

from apps.sad.alertes_auto import envoyer_toutes_les_alertes


class Command(BaseCommand):
    help = (
        "Envoie MAINTENANT les alertes email en attente (stock bas/dormant, "
        "événements, saison). Normalement inutile : le serveur le fait "
        "automatiquement (apps/sad/alertes_auto.py). Sert à forcer/tester."
    )

    def handle(self, *args, **options):
        total = 0
        for commercant, envoyees in envoyer_toutes_les_alertes():
            total += envoyees
            email = commercant.utilisateur.email or "(AUCUN EMAIL)"
            self.stdout.write(
                f"[{commercant.nom_boutique}] {envoyees} alerte(s) envoyée(s) à {email}"
            )
        self.stdout.write(self.style.SUCCESS(f"Terminé : {total} alerte(s) au total."))
