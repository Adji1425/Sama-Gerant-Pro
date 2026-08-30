import getpass
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.users.models import Utilisateur, Administrateur


class Command(BaseCommand):
    """
    Crée un compte administrateur complet : un Utilisateur (role='admin',
    is_staff=True, is_superuser=True pour l'accès à /admin/) ET son
    profil Administrateur associé (nécessaire pour passer le décorateur
    admin_required, qui vérifie hasattr(request.user, 'administrateur')).

    Le simple `python manage.py createsuperuser` de Django ne suffit pas
    ici : il ne renseigne pas le champ 'role' et ne crée pas la ligne
    Administrateur, donc le compte resterait bloqué sur les pages admin.

    Usage :
        python manage.py creer_admin
        python manage.py creer_admin --username admin --email admin@sama.pro
    """
    help = "Crée un compte administrateur (Utilisateur + profil Administrateur)."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help="Nom d'utilisateur")
        parser.add_argument('--email', type=str, help="Email")
        parser.add_argument('--prenom', type=str, help="Prénom")
        parser.add_argument('--nom', type=str, help="Nom")
        parser.add_argument('--telephone', type=str, help="Téléphone")

    def handle(self, *args, **options):
        username = options.get('username') or input("Nom d'utilisateur : ").strip()
        if not username:
            raise CommandError("Le nom d'utilisateur est obligatoire.")
        if Utilisateur.objects.filter(username=username).exists():
            raise CommandError(f"L'utilisateur '{username}' existe déjà.")

        email = options.get('email') or input("Email : ").strip()
        prenom = options.get('prenom') or input("Prénom : ").strip()
        nom = options.get('nom') or input("Nom : ").strip()
        telephone = options.get('telephone') or input("Téléphone (optionnel) : ").strip()

        password = getpass.getpass("Mot de passe : ")
        password_confirm = getpass.getpass("Confirmer le mot de passe : ")
        if password != password_confirm:
            raise CommandError("Les mots de passe ne correspondent pas.")
        if not password:
            raise CommandError("Le mot de passe ne peut pas être vide.")

        with transaction.atomic():
            utilisateur = Utilisateur.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=prenom,
                last_name=nom,
                telephone=telephone,
                role='admin',
            )
            # Accès à l'admin Django (/admin/) en plus de l'espace admin
            # interne de l'application.
            utilisateur.is_staff = True
            utilisateur.is_superuser = True
            utilisateur.save()

            Administrateur.objects.create(utilisateur=utilisateur)

        self.stdout.write(self.style.SUCCESS(
            f"✓ Administrateur '{username}' créé avec succès."
        ))