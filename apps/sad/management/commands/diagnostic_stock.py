from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from apps.produits.models import Produit
from apps.sad.utils import _alerte_deja_envoyee


class Command(BaseCommand):
    help = (
        "Explique, produit par produit, pourquoi l'email de stock bas est "
        "envoyé ou non. Avec --envoyer, tente un vrai envoi de test."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--envoyer', action='store_true',
            help="Envoie un email de test à chaque commerçant concerné.",
        )

    def handle(self, *args, **opts):
        self.stdout.write(f"Backend email : {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Expéditeur    : {settings.EMAIL_FROM or '(vide)'}")
        if 'console' in settings.EMAIL_BACKEND:
            self.stdout.write(self.style.ERROR(
                "-> MODE CONSOLE : EMAIL_HOST_USER / EMAIL_HOST_PASSWORD absents "
                "du .env, les emails ne partent pas vraiment."
            ))
        self.stdout.write("")

        testes = set()
        for p in Produit.objects.select_related('commercant__utilisateur').order_by('commercant_id', 'nom'):
            c = p.commercant
            email = c.utilisateur.email
            if p.statut != 'actif':
                raison = f"IGNORÉ : statut « {p.statut} » (seuls les produits actifs sont surveillés)"
            elif not p.est_en_alerte():
                raison = "pas d'alerte : stock au-dessus du seuil"
            elif not email:
                raison = "PAS D'EMAIL : le compte du commerçant n'a pas d'adresse email"
            elif _alerte_deja_envoyee(c, 'stock_bas', f"Stock bas : {p.nom}", jours=7):
                raison = ("Déjà alerté il y a moins de 7 jours (rappel à l'ouverture du "
                          "tableau de bord). Une vente qui franchit le seuil envoie "
                          "toujours un email, sans dépendre de ça.")
            else:
                raison = "OK : un email partira à la prochaine commande qui touche ce produit"
            self.stdout.write(
                f"[{c.nom_boutique}] {p.nom} — stock {p.quantite} / seuil {p.seuil_alerte} "
                f"— email : {email or '(aucun)'}\n    {raison}"
            )

            if opts['envoyer'] and email and c.pk not in testes:
                testes.add(c.pk)
                try:
                    send_mail(
                        "[Sama-Gérant Pro] Test d'email", "Ceci est un test d'envoi.",
                        settings.EMAIL_FROM, [email], fail_silently=False,
                    )
                    self.stdout.write(self.style.SUCCESS(f"    Test envoyé à {email}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ÉCHEC d'envoi à {email} : {e!r}"))