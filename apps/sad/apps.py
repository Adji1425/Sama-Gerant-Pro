from django.apps import AppConfig


class SadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sad'

    def ready(self):
        # Envoi automatique des alertes email (stock, événements, saison)
        # tant que le serveur tourne. Voir apps/sad/alertes_auto.py.
        from . import alertes_auto
        alertes_auto.demarrer()
