from django.db import models
from apps.commandes.models import Commande


class Facture(models.Model):
    commande = models.OneToOneField(
        Commande, on_delete=models.CASCADE, related_name='facture'
    )
    pdf_url = models.FileField(upload_to='factures/', blank=True, null=True)
    date_facture = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Facture"

    def __str__(self):
        return f"Facture #{self.id} - Commande #{self.commande.id}"
