from django.utils import timezone
from datetime import timedelta
from apps.produits.models import Produit
from apps.commandes.models import DetailsCommande

# Saisons sénégalaises (constantes dans settings, pas de table BDD)
SAISONS_SENEGAL = {
    "hivernage":   {"debut": (6, 1),  "fin": (10, 31)},
    "saison_seche": {"debut": (11, 1), "fin": (5, 31)},
}


def calculer_marge_nette(produit):
    return produit.prix_vente - produit.prix_achat - produit.frais_packaging


def identifier_top_produits(commercant, limite=5):
    from django.db.models import Sum
    return (
        DetailsCommande.objects
        .filter(produit__commercant=commercant)
        .values('produit__nom', 'produit__id')
        .annotate(total_vendu=Sum('quantite'))
        .order_by('-total_vendu')[:limite]
    )


def identifier_stocks_dormants(commercant, jours=60):
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


def get_saison_actuelle():
    mois = timezone.now().date().month
    if 6 <= mois <= 10:
        return "hivernage"
    return "saison_seche"
