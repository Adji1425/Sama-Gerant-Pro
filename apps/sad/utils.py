from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum

# Saisons sénégalaises — constantes, pas de table BDD
SAISONS_SENEGAL = {
    "hivernage": {
        "debut": (6, 1),
        "fin": (10, 31),
        "conseil": "Pensez aux imperméables, bottes et parapluies !"
    },
    "saison_seche": {
        "debut": (11, 1),
        "fin": (5, 31),
        "conseil": "Saison sèche : forte demande en ventilateurs et crèmes."
    },
}


def get_saison_actuelle():
    mois = timezone.now().date().month
    return "hivernage" if 6 <= mois <= 10 else "saison_seche"


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
    """Crée une Notification pour chaque produit en alerte de stock (évite les doublons non lus)."""
    from apps.produits.models import Produit
    from apps.notifications.models import Notification

    for produit in Produit.objects.filter(commercant=commercant, statut='actif'):
        if produit.est_en_alerte():
            deja_notifie = Notification.objects.filter(
                commercant=commercant, type='stock_bas', lu=False,
                titre__icontains=produit.nom,
            ).exists()
            if not deja_notifie:
                Notification.objects.create(
                    commercant=commercant,
                    titre=f"Stock bas : {produit.nom}",
                    message=f"Il reste {produit.quantite} unité(s) de {produit.nom} (seuil : {produit.seuil_alerte}).",
                    type='stock_bas',
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