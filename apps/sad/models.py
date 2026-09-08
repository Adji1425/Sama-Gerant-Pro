from django.db import models


class ConfigurationClimatique(models.Model):
    """
    Textes affichés au commerçant selon la saison climatique détectée
    (§5.3.2 du cahier des charges) : conseil + icône, paramétrables par
    l'administrateur sans toucher au code.

    La saison elle-même n'est PLUS déterminée par une plage de dates :
    elle est détectée en temps réel à partir des données météo réelles
    à Dakar (précipitations + températures, API Open-Meteo — voir
    apps/sad/utils.py). Ce modèle ne sert qu'à éditer le texte/icône
    affichés pour chaque saison détectée.
    """
    CODE_CHOICES = [
        ('hivernage', 'Hivernage'),
        ('saison_seche_fraiche', 'Saison sèche fraîche (harmattan)'),
        ('saison_seche_chaude', 'Saison sèche chaude'),
    ]

    nom = models.CharField(
        max_length=100,
        help_text="Ex : Hivernage, Saison sèche fraîche"
    )
    code = models.CharField(
        max_length=50, unique=True, choices=CODE_CHOICES,
        help_text="Saison à laquelle ce texte correspond (détectée via l'API météo)."
    )
    conseil = models.TextField(
        help_text="Conseil affiché au commerçant durant cette saison"
    )
    icone = models.CharField(
        max_length=50, default='bi-cloud-sun',
        help_text="Classe Bootstrap Icons, ex : bi-cloud-rain-heavy, bi-sun"
    )
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuration climatique"
        verbose_name_plural = "Configurations climatiques"
        ordering = ['code']

    def __str__(self):
        return self.nom
