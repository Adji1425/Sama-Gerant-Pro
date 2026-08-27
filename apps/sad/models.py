from django.db import models


class ConfigurationClimatique(models.Model):
    """
    Définition paramétrable des saisons climatiques utilisées par le SAD
    pour adapter ses conseils au commerçant (§5.3.2 du cahier des charges).

    Remplace l'ancien dictionnaire SAISONS_SENEGAL codé en dur dans
    apps/sad/utils.py : désormais géré par l'administrateur depuis une
    page dédiée, sans toucher au code.
    """
    MOIS_CHOICES = [(i, i) for i in range(1, 13)]

    nom = models.CharField(
        max_length=100, unique=True,
        help_text="Ex : Hivernage, Saison sèche"
    )
    code = models.SlugField(
        max_length=50, unique=True,
        help_text="Identifiant technique (sans espace), ex : hivernage"
    )
    mois_debut = models.PositiveSmallIntegerField(choices=MOIS_CHOICES)
    jour_debut = models.PositiveSmallIntegerField(default=1)
    mois_fin = models.PositiveSmallIntegerField(choices=MOIS_CHOICES)
    jour_fin = models.PositiveSmallIntegerField(default=1)
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
        ordering = ['mois_debut', 'jour_debut']

    def __str__(self):
        return self.nom

    def contient_date(self, date):
        """
        Vrai si `date` (objet date) tombe dans la période définie.
        Gère les périodes à cheval sur le nouvel an
        (ex : 1 novembre → 31 mai).
        """
        debut = (self.mois_debut, self.jour_debut)
        fin = (self.mois_fin, self.jour_fin)
        courant = (date.month, date.day)
        if debut <= fin:
            return debut <= courant <= fin
        return courant >= debut or courant <= fin