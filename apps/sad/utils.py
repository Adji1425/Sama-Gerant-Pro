from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count

# Saisons sénégalaises — pas de table BDD, constantes suffisent
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
    from apps.commandes.models import DetailsCommande
    return (
        DetailsCommande.objects
        .filter(produit__commercant=commercant)
        .values('produit__id', 'produit__nom')
        .annotate(total_vendu=Sum('quantite'))
        .order_by('-total_vendu')[:limite]
    )


def identifier_stocks_dormants(commercant, jours=60):
    from apps.produits.models import Produit
    from apps.commandes.models import DetailsCommande
    date_limite = timezone.now().date() - timedelta(days=jours)
    produits_actifs = Produit.objects.filter(
        commercant=commercant, statut='actif'
    )
    dormants = []
    for produit in produits_actifs:
        derniere_vente = (
            DetailsCommande.objects
            .filter(produit=produit)
            .order_by('-commande__date_commande')
            .first()
        )
        if not derniere_vente or \
           derniere_vente.commande.date_commande.date() < date_limite:
            dormants.append(produit)
    return dormants


def calculer_chiffre_affaires(commercant, periode_jours=30):
    from apps.commandes.models import Commande
    date_debut = timezone.now() - timedelta(days=periode_jours)
    commandes = Commande.objects.filter(
        client__utilisateur__in=[],
        date_commande__gte=date_debut,
        statut='livree'
    )
    return sum(c.montant_total for c in commandes)


def verifier_alertes_stock(commercant):
    """Génère des notifications automatiques pour les stocks bas et dormants"""
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
                    'message': f"Le stock de '{produit.nom}' est à "
                               f"{produit.quantite} unité(s). "
                               f"Seuil d'alerte : {produit.seuil_alerte}.",
                    'type': 'stock_bas',
                    'lu': False,
                }
            )