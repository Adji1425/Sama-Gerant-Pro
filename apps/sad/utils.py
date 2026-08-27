from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings


def envoyer_email_alerte(commercant, sujet, message):
    """
    Envoie un email d'alerte au commerçant (stock bas / stock dormant).
    fail_silently=True : si le SMTP n'est pas configuré (dev local),
    l'application continue de fonctionner normalement.
    """
    destinataire = getattr(commercant.utilisateur, 'email', None)
    if not destinataire:
        return
    send_mail(
        subject=f"[Sama-Gérant Pro] {sujet}",
        message=message,
        from_email=settings.EMAIL_HOST_USER or None,
        recipient_list=[destinataire],
        fail_silently=True,
    )

def get_saison_actuelle():
    """
    Retourne la ConfigurationClimatique (saison) active correspondant à
    la date du jour, telle que paramétrée par l'administrateur (§5.3.2).

    Remplace l'ancien dictionnaire SAISONS_SENEGAL codé en dur : les
    saisons sont maintenant des lignes en base, modifiables sans toucher
    au code, via la page « Configuration climatique » de l'espace admin.
    Retourne None si aucune saison active ne couvre la date du jour
    (ex : configuration incomplète).
    """
    from apps.sad.models import ConfigurationClimatique

    aujourdhui = timezone.now().date()
    for config in ConfigurationClimatique.objects.filter(actif=True):
        if config.contient_date(aujourdhui):
            return config
    return None


def calculer_marge_nette(produit):
    return round(
        produit.prix_vente - produit.prix_achat - produit.frais_packaging, 2
    )


def identifier_top_produits(commercant, limite=5):
    # ✅ CORRIGÉ : LignePanier au lieu de DetailsCommande
    from apps.commandes.models import LignePanier
    return (
        LignePanier.objects
        .filter(
            produit__commercant=commercant,
            commande__isnull=False,          # Seulement les lignes validées
            commande__statut='livree'
        )
        .values('produit__id', 'produit__nom')
        .annotate(total_vendu=Sum('quantite'))
        .order_by('-total_vendu')[:limite]
    )


def identifier_stocks_dormants(commercant, jours=60):
    # ✅ CORRIGÉ : LignePanier au lieu de DetailsCommande
    from apps.produits.models import Produit
    from apps.commandes.models import LignePanier

    date_limite = timezone.now().date() - timedelta(days=jours)
    produits_actifs = Produit.objects.filter(
        commercant=commercant, statut='actif'
    )
    dormants = []
    for produit in produits_actifs:
        derniere_vente = (
            LignePanier.objects
            .filter(
                produit=produit,
                commande__isnull=False
            )
            .order_by('-commande__date_commande')
            .first()
        )
        if not derniere_vente or \
           derniere_vente.commande.date_commande.date() < date_limite:
            dormants.append(produit)
    return dormants


def calculer_chiffre_affaires(commercant, periode_jours=30):
    from apps.commandes.models import Commande
    from apps.users.models import Client

    date_debut = timezone.now() - timedelta(days=periode_jours)
    # Trouver les clients du commerçant via leurs commandes
    commandes = Commande.objects.filter(
        lignes__produit__commercant=commercant,
        date_commande__gte=date_debut,
        statut='livree'
    ).distinct()
    return sum(c.montant_total for c in commandes)


def verifier_alertes_stock(commercant):
    """Génère des notifications pour les stocks bas et dormants"""
    from apps.produits.models import Produit
    from apps.notifications.models import Notification

    produits = Produit.objects.filter(
        commercant=commercant, statut='actif'
    )
    for produit in produits:
        if produit.est_en_alerte():
            Notification.objects.get_or_create(
                commercant=commercant,
                titre=f"Stock bas : {produit.nom}",
                defaults={
                    'message': (
                        f"Le stock de '{produit.nom}' est à "
                        f"{produit.quantite} unité(s). "
                        f"Seuil d'alerte : {produit.seuil_alerte}."
                    ),
                    'type': 'stock_bas',
                    'lu': False,
                }
            )

        # Vérifier stocks dormants
        dormants = identifier_stocks_dormants(
            commercant, jours=produit.seuil_dormant
        )
        for p in dormants:
            Notification.objects.get_or_create(
                commercant=commercant,
                titre=f"Stock dormant : {p.nom}",
                defaults={
                    'message': (
                        f"'{p.nom}' n'a pas été vendu depuis plus de "
                        f"{p.seuil_dormant} jours. "
                        f"Pensez à faire une promotion !"
                    ),
                    'type': 'stock_dormant',
                    'lu': False,
                }
            )


# --- Génération automatique des notifications (déclenchée à chaque visite du dashboard SAD) ---

def generer_notifications_stock(commercant):
    """
    Crée une Notification (in-app) + envoie un email pour chaque produit
    en alerte de stock bas OU en stock dormant (évite les doublons non lus).
    """
    from apps.produits.models import Produit
    from apps.notifications.models import Notification

    produits = Produit.objects.filter(commercant=commercant, statut='actif')

    for produit in produits:
        # --- Stock bas ---
        if produit.est_en_alerte():
            deja_notifie = Notification.objects.filter(
                commercant=commercant, type='stock_bas', lu=False,
                titre__icontains=produit.nom,
            ).exists()
            if not deja_notifie:
                message = (
                    f"Il reste {produit.quantite} unité(s) de {produit.nom} "
                    f"(seuil : {produit.seuil_alerte})."
                )
                Notification.objects.create(
                    commercant=commercant,
                    titre=f"Stock bas : {produit.nom}",
                    message=message,
                    type='stock_bas',
                )
                envoyer_email_alerte(
                    commercant,
                    sujet=f"Stock bas — {produit.nom}",
                    message=message,
                )

    # --- Stock dormant ---
    for produit in identifier_stocks_dormants(commercant):
        deja_notifie = Notification.objects.filter(
            commercant=commercant, type='stock_dormant', lu=False,
            titre__icontains=produit.nom,
        ).exists()
        if not deja_notifie:
            message = (
                f"'{produit.nom}' n'a pas été vendu depuis plus de "
                f"{produit.seuil_dormant} jours. Pensez à faire une promotion "
                f"ou à libérer de la trésorerie sur ce produit."
            )
            Notification.objects.create(
                commercant=commercant,
                titre=f"Stock dormant : {produit.nom}",
                message=message,
                type='stock_dormant',
            )
            envoyer_email_alerte(
                commercant,
                sujet=f"Stock dormant — {produit.nom}",
                message=message,
            )


def repartition_geographique_commandes(commercant):
    """
    Analyse de répartition géographique des commandes (§5.4) : regroupe
    les commandes contenant des produits du commerçant par région,
    avec le nombre de commandes et le chiffre d'affaires correspondant.
    Aide le commerçant à identifier ses zones de vente les plus actives.
    """
    from apps.commandes.models import Commande

    commandes = (
        Commande.objects
        .filter(
            lignes__produit__commercant=commercant,
            statut__in=['en_preparation', 'livree'],
        )
        .distinct()
    )

    stats_par_region = {}
    for commande in commandes.select_related('region'):
        nom_region = commande.region.nom if commande.region else "Non renseignée"
        entry = stats_par_region.setdefault(
            nom_region, {'region': nom_region, 'nb_commandes': 0, 'montant_total': 0}
        )
        entry['nb_commandes'] += 1
        entry['montant_total'] += commande.montant_total

    return sorted(
        stats_par_region.values(),
        key=lambda e: e['nb_commandes'],
        reverse=True,
    )


def generer_notifications_evenements(commercant, jours=21):
    """Alerte prévisionnelle 15-30 jours avant un événement (Tabaski, Magal, Korité...)."""
    from apps.notifications.models import Notification
    from apps.evenements.models import EvenementSAD

    for evenement in EvenementSAD.objects.all():
        if evenement.est_proche(jours=jours):
            deja_notifie = Notification.objects.filter(
                commercant=commercant, type='evenement', lu=False,
                titre__icontains=evenement.nom_evenement,
            ).exists()
            if not deja_notifie:
                Notification.objects.create(
                    commercant=commercant,
                    titre=f"Événement à venir : {evenement.nom_evenement}",
                    message=evenement.conseil_affiche,
                    type='evenement',
                )