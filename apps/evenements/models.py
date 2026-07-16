from django.db import models
from django.utils import timezone
from datetime import timedelta


class EvenementSAD(models.Model):
    """
    Événements religieux et culturels sénégalais.
    Configurés par l'administrateur.
    """
    nom_evenement = models.CharField(max_length=150)
    date_debut = models.DateField()
    date_fin = models.DateField()
    conseil_affiche = models.TextField(
        help_text="Conseil affiché au commerçant avant cet événement"
    )

    class Meta:
        verbose_name = "Événement SAD"
        verbose_name_plural = "Événements SAD"
        ordering = ['date_debut']

    def __str__(self):
        return self.nom_evenement

    def est_proche(self, jours=21):
        """True si l'événement arrive dans moins de X jours"""
        today = timezone.now().date()
        return today <= self.date_debut <= today + timedelta(days=jours)

    def est_en_cours(self):
        today = timezone.now().date()
        return self.date_debut <= today <= self.date_fin