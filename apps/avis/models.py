from django.db import models
from apps.users.models import Client
from apps.produits.models import Produit
from apps.commandes.models import DetailsCommande


class Avis(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='avis'
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.CASCADE, related_name='avis_set'
    )
    details_commande = models.ForeignKey(
        DetailsCommande, on_delete=models.SET_NULL,
        null=True, related_name='avis'
    )
    note = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaire = models.TextField(blank=True)
    date_avis = models.DateField(auto_now_add=True)
    verifie_achat = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Avis"
        unique_together = ('client', 'produit')

    def __str__(self):
        return f"Avis {self.note}/5 sur {self.produit.nom}"
