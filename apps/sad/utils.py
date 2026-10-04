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
            from_email=settings.EMAIL_FROM,
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


def calculer_temps_vente(produit):
    """
    Temps moyen et temps minimum (en jours) entre deux ventes
    consécutives d'un produit, à partir de ses commandes livrées.
    Retourne (temps_moyen, temps_minimum), ou (None, None) si le produit
    a moins de 2 ventes livrées (pas assez d'historique pour calculer un
    écart).
    """
    from apps.commandes.models import LignePanier

    dates = list(
        LignePanier.objects.filter(
            produit=produit,
            commande__isnull=False,
            commande__statut='livree'
        )
        .order_by('commande__date_commande')
        .values_list('commande__date_commande', flat=True)
    )
    if len(dates) < 2:
        return None, None

    ecarts = [
        (dates[i] - dates[i - 1]).days
        for i in range(1, len(dates))
    ]
    ecarts = [e for e in ecarts if e >= 0]
    if not ecarts:
        return None, None

    temps_moyen = round(sum(ecarts) / len(ecarts), 1)
    temps_minimum = min(ecarts)
    return temps_moyen, temps_minimum


def suggerer_reapprovisionnement(commercant, limite=5):
    """
    §5.4 du cahier des charges : "Sur la base de ces calculs (temps
    minimum et moyen de vente), il suggère au commerçant des
    réapprovisionnements prioritaires."

    Un produit est jugé prioritaire quand il se vend régulièrement
    (temps moyen de vente connu, ≤ 15 jours entre deux ventes) ET que
    son stock actuel est bas ou proche du seuil d'alerte : c'est un
    produit qui rapporte, mais qui risque la rupture avant le prochain
    réapprovisionnement si rien n'est fait.
    """
    from apps.produits.models import Produit

    suggestions = []
    produits = Produit.objects.filter(commercant=commercant, statut='actif')

    for produit in produits:
        temps_moyen, temps_minimum = calculer_temps_vente(produit)
        if temps_moyen is None:
            continue  # pas assez de ventes livrées pour ce produit

        stock_bas_ou_proche = produit.quantite <= (produit.seuil_alerte * 2)
        se_vend_vite = temps_moyen <= 15

        if stock_bas_ou_proche and se_vend_vite:
            suggestions.append({
                'produit': produit,
                'temps_moyen': temps_moyen,
                'temps_minimum': temps_minimum,
                'stock_actuel': produit.quantite,
            })

    # Priorité aux produits qui se vendent le plus vite (temps moyen le
    # plus court), c'est-à-dire les plus urgents à réapprovisionner.
    suggestions.sort(key=lambda s: s['temps_moyen'])
    return suggestions[:limite]


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

def _alerte_deja_envoyee(commercant, type_alerte, titre, jours):
    """
    Anti-doublon basé sur la DATE d'envoi (jamais sur « lu / non lu ») :
    vrai si la même alerte (même type, même titre exact) a déjà été envoyée
    à ce commerçant dans les `jours` derniers jours. La table Notification
    sert uniquement de journal des alertes envoyées.
    """
    from apps.notifications.models import Notification

    depuis = timezone.now() - timedelta(days=jours)
    return Notification.objects.filter(
        commercant=commercant, type=type_alerte, titre=titre,
        date_envoi__gte=depuis,
    ).exists()


def _envoyer_alerte(commercant, type_alerte, titre, sujet, message):
    """Journalise l'alerte puis envoie l'email au commerçant."""
    from apps.notifications.models import Notification

    Notification.objects.create(
        commercant=commercant, titre=titre, message=message, type=type_alerte,
    )
    envoyer_email_alerte(commercant, sujet=sujet, message=message)


def verifier_stock_produit(produit, ancienne_quantite=None):
    """
    Stock bas : envoie l'email d'alerte au commerçant.

    - Appelée depuis une VENTE (`ancienne_quantite` renseignée) : l'email
      part au moment précis où le stock FRANCHIT le seuil, puis une seconde
      fois s'il tombe à 0 (rupture).
    - Appelée sans `ancienne_quantite` (ouverture du tableau de bord) :
      rappel au plus une fois tous les 7 jours tant que le produit reste
      en stock bas.

    Retourne True si un email a été envoyé.
    """
    if produit.statut != 'actif' or not produit.est_en_alerte():
        return False

    titre = f"Stock bas : {produit.nom}"

    if ancienne_quantite is None:
        envoyer = not _alerte_deja_envoyee(
            produit.commercant, 'stock_bas', titre, jours=7
        )
    else:
        franchit_seuil = ancienne_quantite > produit.seuil_alerte
        rupture = produit.quantite <= 0 < ancienne_quantite
        envoyer = franchit_seuil or rupture

    if not envoyer:
        return False

    if produit.quantite <= 0:
        message = (
            f"{produit.nom} est en rupture de stock (seuil : "
            f"{produit.seuil_alerte}). Réapprovisionnez-le rapidement pour "
            f"ne pas perdre de ventes."
        )
    else:
        message = (
            f"Il reste {produit.quantite} unité(s) de {produit.nom} "
            f"(seuil : {produit.seuil_alerte}). Pensez à réapprovisionner."
        )
    _envoyer_alerte(
        produit.commercant, 'stock_bas', titre,
        f"Stock bas — {produit.nom}", message,
    )
    return True


def generer_notifications_stock(commercant):
    """
    Envoie les alertes email de stock bas ET de stock dormant pour les
    produits du commerçant. Anti-doublon par date (voir
    `_alerte_deja_envoyee`) : un produit ne génère jamais plus d'un rappel
    par période, quelle que soit la lecture des notifications.
    """
    from apps.produits.models import Produit

    for produit in Produit.objects.filter(commercant=commercant, statut='actif'):
        verifier_stock_produit(produit)

    # --- Stock dormant : rappel au plus une fois tous les 30 jours ---
    for produit in identifier_stocks_dormants(commercant):
        titre = f"Stock dormant : {produit.nom}"
        if _alerte_deja_envoyee(commercant, 'stock_dormant', titre, jours=30):
            continue
        message = (
            f"'{produit.nom}' n'a pas été vendu depuis plus de "
            f"{produit.seuil_dormant} jours. Pensez à faire une promotion "
            f"ou à libérer de la trésorerie sur ce produit."
        )
        _envoyer_alerte(
            commercant, 'stock_dormant', titre,
            f"Stock dormant — {produit.nom}", message,
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


def historique_evenement(commercant, evenement, jours_avant=21, limite=5):
    """
    Bilan des ventes du commerçant lors de la DERNIÈRE édition passée du
    même événement (ex : Tabaski de l'an dernier), pour lui suggérer de
    bien se réapprovisionner quand l'événement revient.

    Les éditions sont reconnues par le nom : l'administrateur ajoute une
    nouvelle ligne chaque année avec le même nom (« Tabaski »...).
    La période analysée commence `jours_avant` jours AVANT le début de
    l'événement passé, car les achats se font surtout dans la phase de
    préparation. Les commandes annulées sont ignorées.

    Retourne None s'il n'y a pas d'édition passée ou pas de ventes.
    """
    from apps.evenements.models import EvenementSAD
    from apps.commandes.models import LignePanier

    precedent = (
        EvenementSAD.objects
        .filter(nom_evenement__iexact=evenement.nom_evenement,
                date_fin__lt=evenement.date_debut)
        .order_by('-date_debut')
        .first()
    )
    if precedent is None:
        return None

    debut = precedent.date_debut - timedelta(days=jours_avant)
    lignes = (
        LignePanier.objects
        .filter(
            produit__commercant=commercant,
            commande__isnull=False,
            commande__date_commande__date__range=(debut, precedent.date_fin),
        )
        .exclude(commande__statut='annulee')
        .values('produit__id', 'produit__nom', 'produit__quantite')
        .annotate(total_vendu=Sum('quantite'))
        .order_by('-total_vendu')[:limite]
    )

    produits = []
    for l in lignes:
        vendu = l['total_vendu']
        stock = l['produit__quantite']
        produits.append(SimpleNamespace(
            nom=l['produit__nom'],
            vendu=vendu,
            stock=stock,
            manque=max(vendu - stock, 0),
        ))
    if not produits:
        return None

    return SimpleNamespace(
        precedent=precedent, debut=debut, fin=precedent.date_fin,
        produits=produits,
        a_reapprovisionner=[p for p in produits if p.manque > 0],
    )


def texte_historique_evenement(historique):
    """Version texte (pour les notifications) du bilan ci-dessus."""
    if not historique:
        return ""
    p = historique.precedent
    lignes = [
        f"📊 Lors de « {p.nom_evenement} » ({historique.debut:%d/%m/%Y} au "
        f"{historique.fin:%d/%m/%Y}), vous aviez vendu :"
    ]
    for prod in historique.produits:
        lignes.append(
            f"• {prod.nom} : {prod.vendu} vendu(s) — stock actuel : {prod.stock}"
        )
    if historique.a_reapprovisionner:
        conseils = ", ".join(
            f"{prod.nom} (+{prod.manque})" for prod in historique.a_reapprovisionner
        )
        lignes.append(f"👉 Pensez à réapprovisionner : {conseils}.")
    else:
        lignes.append("✅ Votre stock actuel couvre déjà ces ventes.")
    return "\n".join(lignes)


def generer_notifications_evenements(commercant, jours=21):
    """
    Alerte prévisionnelle avant un événement (Tabaski, Magal, Korité...),
    avec le bilan des ventes de la dernière édition. Envoyée par email,
    une seule fois par événement (fenêtre de 30 jours).
    """
    from apps.evenements.models import EvenementSAD

    for evenement in EvenementSAD.objects.all():
        if not evenement.est_proche(jours=jours):
            continue
        titre = f"Événement à venir : {evenement.nom_evenement}"
        if _alerte_deja_envoyee(commercant, 'evenement', titre, jours=30):
            continue
        _envoyer_alerte(
            commercant, 'evenement', titre,
            f"Événement à venir — {evenement.nom_evenement}",
            _message_evenement(commercant, evenement),
        )


def _message_evenement(commercant, evenement):
    """Conseil de l'admin + bilan des ventes de la dernière édition."""
    texte = evenement.conseil_affiche
    bilan = texte_historique_evenement(
        historique_evenement(commercant, evenement)
    )
    return f"{texte}\n\n{bilan}" if bilan else texte
