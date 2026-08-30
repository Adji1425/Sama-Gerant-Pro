from django.core.management.base import BaseCommand
from apps.users.models import Utilisateur


class Command(BaseCommand):
    """
    Supprime TOUS les utilisateurs (clients, commerçants, administrateurs)
    et, par cascade, tout ce qui en dépend : produits, commandes, paniers,
    factures, avis, notifications, messages, dépenses, favoris.

    Ne sont PAS touchés (rien ne dépend des utilisateurs pour ces tables) :
    Régions, Catégories, Configuration climatique.

    Usage :
        python manage.py reset_comptes
        python manage.py reset_comptes --force   (saute la confirmation)
    """
    help = "Supprime tous les comptes (clients, commerçants, admins) et tout ce qui en dépend."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help="Ne pas demander de confirmation (à utiliser avec prudence)."
        )

    def handle(self, *args, **options):
        total = Utilisateur.objects.count()

        if total == 0:
            self.stdout.write("Aucun utilisateur en base. Rien à faire.")
            return

        self.stdout.write(self.style.WARNING(
            f"\nCeci va supprimer {total} utilisateur(s) et, par cascade :\n"
            f"tous les produits, commandes, paniers, factures, avis,\n"
            f"notifications, messages, dépenses et favoris liés.\n"
        ))

        if not options['force']:
            reponse = input(
                "Tape SUPPRIMER (en majuscules) pour confirmer, "
                "ou n'importe quoi d'autre pour annuler : "
            )
            if reponse != 'SUPPRIMER':
                self.stdout.write(self.style.ERROR("Annulé — aucune suppression effectuée."))
                return

        nb_supprimes, details = Utilisateur.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Suppression terminée : {nb_supprimes} enregistrement(s) au total.\n"
        ))
        for modele, nb in sorted(details.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  - {modele} : {nb}")