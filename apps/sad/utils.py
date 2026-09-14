import logging
from types import SimpleNamespace

from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
import requests

logger = logging.getLogger(__name__)

# Coordonnées de Dakar : point de référence unique pour interroger
# l'API météo (le Sénégal est un petit pays, régime climatique
# globalement homogène à l'échelle d'un dashboard national).
DAKAR_LATITUDE = 14.6928
DAKAR_LONGITUDE = -17.4467

# Seuils utilisés pour interpréter les données météo réelles :
# - plus de 1mm de pluie cumulée sur 7 jours => on est en hivernage
# - sinon, en saison sèche, on distingue "fraîche" (harmattan, nuits
#   fraîches) de "chaude" via la température minimale moyenne relevée
SEUIL_PLUIE_HIVERNAGE_MM = 1.0
SEUIL_TEMPERATURE_FRAICHE_C = 20.0

# Textes affichés si l'administrateur n'a pas (encore) configuré de
# ConfigurationClimatique pour la saison détectée (voir sad/models.py).
# Ce ne sont que des textes de repli pour l'affichage — jamais utilisés
# pour déterminer la saison elle-même, qui vient uniquement de l'API.
SAISON_TEXTES_DEFAUT = {
    'hivernage': {
        'nom': 'Hivernage',
        'icone': 'bi-cloud-rain-heavy',
        'conseil': "Pluies détectées à Dakar cette semaine : anticipez la demande en imperméables, bottes et parapluies.",
    },
    'saison_seche_fraiche': {
        'nom': 'Saison sèche fraîche (harmattan)',
        'icone': 'bi-cloud-fog2',
        'conseil': "Températures matinales fraîches détectées : forte demande de pulls et vestes légères.",
    },
    'saison_seche_chaude': {
        'nom': 'Saison sèche chaude',
        'icone': 'bi-sun',
        'conseil': "Chaleur sèche détectée : forte demande en ventilateurs, crèmes solaires et boissons fraîches.",
    },
}


def envoyer_email_alerte(commercant, sujet, message):
    """
    Envoie un email d'alerte au commerçant (stock bas / stock dormant /
    nouvelle commande). N'échoue jamais bruyamment : les erreurs SMTP
    sont journalisées (voir LOGGING dans settings.py) plutôt que
    silencieusement avalées, pour rester diagnosticable.
    """
    destinataire = getattr(commercant.utilisateur, 'email', None)
    if not destinataire:
        logger.warning(
            "Email d'alerte non envoyé : le commerçant %s n'a pas d'adresse email.",
            commercant,
        )
        return False
    try:
        send_mail(
            subject=f"[Sama-Gérant Pro] {sujet}",
            message=message,
            from_email=settings.EMAIL_HOST_USER or None,
            recipient_list=[destinataire],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception(
            "Échec de l'envoi de l'email d'alerte '%s' au commerçant %s",
            sujet, commercant,
        )
        return False


def _recuperer_meteo_dakar():
    """
    Interroge l'API météo gratuite Open-Meteo (aucune clé requise) pour
    récupérer, pour Dakar, les précipitations et températures réelles
    des 7 derniers jours. Résultat mis en cache 6h pour ne pas
    solliciter l'API à chaque affichage du dashboard. Retourne None si
    l'API est injoignable (pas de réseau, timeout, panne du service...).
    """
    cle_cache = "sad_meteo_dakar"
    donnees = cache.get(cle_cache)
    if donnees is not None:
        return donnees

    try:
        reponse = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": DAKAR_LATITUDE,
                "longitude": DAKAR_LONGITUDE,
                "daily": "precipitation_sum,temperature_2m_min",
                "past_days": 7,
                "forecast_days": 1,
                "timezone": "Africa/Dakar",
            },
            timeout=5,
        )
        reponse.raise_for_status()
        donnees = reponse.json()
        cache.set(cle_cache, donnees, 6 * 60 * 60)  # 6h
        return donnees
    except requests.RequestException:
        logger.warning("API météo Open-Meteo injoignable, saison non détectée.")
        return None


def get_saison_actuelle():
    """
    Détermine la saison actuelle au Sénégal UNIQUEMENT à partir des
    données météo RÉELLES des 7 derniers jours à Dakar, via l'API
    gratuite Open-Meteo (sans clé) — aucune prédiction basée sur le
    calendrier (pas de "de juin à octobre c'est l'hivernage").

    Logique :
    - s'il a plu de façon significative sur la semaine -> hivernage
    - sinon (saison sèche), on distingue via la température minimale
      moyenne relevée : fraîche (harmattan) si nuits fraîches, chaude
      sinon.

    Retourne :
    - la ConfigurationClimatique (nom/icône/conseil éditables par
      l'admin) correspondant à la saison détectée, si elle existe ;
    - à défaut, un objet générique avec les mêmes attributs ;
    - None si l'API météo est injoignable ou renvoie des données
      inexploitables (le dashboard affiche alors "météo indisponible",
      sans deviner de saison).
    """
    from apps.sad.models import ConfigurationClimatique

    donnees = _recuperer_meteo_dakar()
    if not donnees:
        return None

    try:
        quotidien = donnees["daily"]
        precipitations = [p for p in quotidien["precipitation_sum"] if p is not None]
        temps_min = [t for t in quotidien["temperature_2m_min"] if t is not None]
        total_pluie_semaine = sum(precipitations)
    except (KeyError, TypeError):
        return None

    if total_pluie_semaine > SEUIL_PLUIE_HIVERNAGE_MM:
        code = "hivernage"
    elif temps_min:
        temp_min_moyenne = sum(temps_min) / len(temps_min)
        code = (
            "saison_seche_fraiche"
            if temp_min_moyenne < SEUIL_TEMPERATURE_FRAICHE_C
            else "saison_seche_chaude"
        )
    else:
        # Pas de pluie détectée mais température indisponible : on ne
        # peut pas distinguer fraîche/chaude, on retient la saison
        # sèche la plus fréquente par défaut (chaude).
        code = "saison_seche_chaude"

    config = ConfigurationClimatique.objects.filter(code=code, actif=True).first()
    if config:
        return config

    return SimpleNamespace(code=code, **SAISON_TEXTES_DEFAUT[code])



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
    les commandes contenant des produits du commerçant par région, avec
    le nombre de commandes, le chiffre d'affaires, et le TYPE DE PRODUIT
    (catégorie) le plus demandé dans cette région. Aide le commerçant à
    identifier ses zones de vente les plus actives et ce qui s'y vend le
    mieux, pour adapter son offre par localité.
    """
    from apps.commandes.models import Commande, LignePanier

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

    # Produit (catégorie) le plus demandé par région : on agrège les
    # quantités vendues par région + catégorie, puis on ne garde que la
    # catégorie en tête pour chaque région.
    quantites_par_region_categorie = (
        LignePanier.objects
        .filter(
            produit__commercant=commercant,
            commande__isnull=False,
            commande__statut__in=['en_preparation', 'livree'],
        )
        .values('commande__region__nom', 'produit__categorie__nom')
        .annotate(quantite=Sum('quantite'))
        .order_by('commande__region__nom', '-quantite')
    )

    top_categorie_par_region = {}
    for ligne in quantites_par_region_categorie:
        nom_region = ligne['commande__region__nom'] or "Non renseignée"
        # Première occurrence rencontrée pour cette région = la plus
        # vendue (grâce au tri -quantite ci-dessus).
        if nom_region not in top_categorie_par_region:
            top_categorie_par_region[nom_region] = (
                ligne['produit__categorie__nom'] or "Non catégorisé"
            )

    for nom_region, entry in stats_par_region.items():
        entry['top_categorie'] = top_categorie_par_region.get(nom_region, "—")

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