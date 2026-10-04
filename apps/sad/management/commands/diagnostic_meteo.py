import requests
from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.sad.utils import DAKAR_LATITUDE, DAKAR_LONGITUDE, get_saison_actuelle


class Command(BaseCommand):
    help = "Teste l'accès à l'API météo Open-Meteo et affiche la cause exacte d'un échec."

    def handle(self, *args, **options):
        self.stdout.write(f"requests version : {requests.__version__}")
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": DAKAR_LATITUDE, "longitude": DAKAR_LONGITUDE,
                    "daily": "precipitation_sum,temperature_2m_min",
                    "past_days": 7, "forecast_days": 1, "timezone": "Africa/Dakar",
                },
                timeout=(5, 15),
            )
            self.stdout.write(f"Statut HTTP : {r.status_code}")
            r.raise_for_status()
            quotidien = r.json()["daily"]
            self.stdout.write(f"Pluie (mm) 8 derniers jours : {quotidien['precipitation_sum']}")
            self.stdout.write(f"Température min (°C)        : {quotidien['temperature_2m_min']}")
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"ÉCHEC : {exc!r}"))
            self.stdout.write(
                "Pistes : pas d'internet à cet instant, pare-feu/antivirus ou proxy "
                "qui bloque Python (le navigateur passe mais pas Python), "
                "date/heure du PC incorrecte (erreur SSL), DNS lent."
            )
            return

        cache.delete("sad_meteo_dakar")
        saison = get_saison_actuelle()
        self.stdout.write(self.style.SUCCESS(
            f"Saison détectée : {saison.nom if saison else 'aucune'}"
        ))
