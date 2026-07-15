from django.db import models


class EvenementSAD(models.Model):
    nom_evenement = models.CharField(max_length=150)
    date_debut = models.DateField()
    date_fin = models.DateField()
    conseil_affiche = models.TextField(
        help_text="Conseil affiché au commerçant avant cet événement"
    )

    class Meta:
        verbose_name = "Événement SAD"
        ordering = ['date_debut']

    def __str__(self):
        return self.nom_evenement

    def est_proche(self, jours=21):
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now().date()
        return today <= self.date_debut <= today + timedelta(days=jours)
