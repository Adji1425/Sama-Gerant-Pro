"""
Envoi AUTOMATIQUE des alertes email (stock bas/dormant, événements, saison).

Un petit fil d'exécution (thread) démarre avec le serveur Django et relance
la vérification toutes les `ALERTES_AUTO_INTERVALLE_HEURES` heures. Aucune
commande à lancer à la main : tant que le site tourne, les alertes partent,
comme l'email « nouvelle commande ».

Pas de doublon, même si la vérification tourne souvent : chaque alerte a sa
propre période de silence (voir apps/sad/utils.py, `_alerte_deja_envoyee`).

Désactivation : ALERTES_AUTO=0 dans le .env.
"""
import logging
import os
import sys
import threading
import time

from django.conf import settings
from django.db import close_old_connections, connection

logger = logging.getLogger(__name__)

# Clé arbitraire du verrou PostgreSQL : empêche deux processus (plusieurs
# workers en production) de lancer la vérification en même temps.
_CLE_VERROU = 7_340_021
_thread = None


def envoyer_toutes_les_alertes():
    """
    Parcourt tous les commerçants et envoie leurs alertes en attente.
    Retourne la liste de tuples (commercant, nombre_d_alertes_envoyees).
    """
    from apps.notifications.models import Notification
    from apps.sad.utils import (
        generer_alerte_saison, generer_notifications_evenements,
        generer_notifications_stock,
    )
    from apps.users.models import Commercant

    resultats = []
    for commercant in Commercant.objects.select_related('utilisateur'):
        # Une erreur sur un commerçant ne doit pas bloquer les autres.
        try:
            avant = Notification.objects.filter(commercant=commercant).count()
            generer_notifications_stock(commercant)
            generer_notifications_evenements(commercant)
            generer_alerte_saison(commercant)
            apres = Notification.objects.filter(commercant=commercant).count()
            resultats.append((commercant, apres - avant))
        except Exception:
            logger.exception("Alertes impossibles pour %s", commercant)
    return resultats


def _prendre_verrou():
    if connection.vendor != 'postgresql':
        return True
    with connection.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", [_CLE_VERROU])
        return bool(cur.fetchone()[0])


def _liberer_verrou():
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s)", [_CLE_VERROU])


def une_passe():
    """Une vérification complète. Ne lève jamais d'exception."""
    close_old_connections()
    try:
        if not _prendre_verrou():
            return 0          # un autre processus s'en occupe déjà
        try:
            total = sum(n for _, n in envoyer_toutes_les_alertes())
            if total:
                logger.info("Alertes automatiques : %d email(s) envoyé(s).", total)
            return total
        finally:
            _liberer_verrou()
    except Exception:
        logger.exception("Vérification automatique des alertes impossible")
        return 0
    finally:
        close_old_connections()


def _boucle(delai_initial, intervalle):
    time.sleep(delai_initial)         # laisse le serveur finir de démarrer
    while True:
        une_passe()
        time.sleep(intervalle)


def doit_demarrer(argv=None, env=None):
    """
    Faut-il lancer le planificateur dans CE processus ?
    - désactivé si ALERTES_AUTO=0 ;
    - jamais pendant migrate, shell, test, makemigrations, envoyer_alertes... ;
    - `runserver` : uniquement dans le processus qui sert réellement le site
      (le rechargeur automatique en crée deux) ;
    - serveur de production (daphne, gunicorn, uvicorn...) : oui.
    """
    argv = sys.argv if argv is None else argv
    env = os.environ if env is None else env
    if not getattr(settings, 'ALERTES_AUTO', True):
        return False
    if argv and os.path.basename(argv[0]) == 'manage.py':
        if len(argv) < 2 or argv[1] != 'runserver':
            return False
        return env.get('RUN_MAIN') == 'true' or '--noreload' in argv
    return True


def demarrer():
    """Lance le planificateur (une seule fois par processus)."""
    global _thread
    if (_thread is not None and _thread.is_alive()) or not doit_demarrer():
        return False
    _thread = threading.Thread(
        target=_boucle,
        args=(
            float(getattr(settings, 'ALERTES_AUTO_DELAI_SECONDES', 30)),
            float(getattr(settings, 'ALERTES_AUTO_INTERVALLE_HEURES', 6)) * 3600,
        ),
        name='sgp-alertes-auto',
        daemon=True,   # s'arrête avec le serveur
    )
    _thread.start()
    return True
