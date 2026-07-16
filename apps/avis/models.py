from django.db import models
from apps.users.models import Client
from apps.produits.models import Produit
from apps.commandes.models import DetailsCommande


class Avis(models.Model):
    """
    Avis laissé par un client sur un produit.
    Uniquement si l'achat est vérifié via DetailsCommande.
    """
    NOTE_CHOICES = [(i, f"{i} étoile{'s' if i > 1 else ''}") for i in range(1, 6)]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='avis'
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='avis_set'
    )
    # Lien vers l'achat pour vérification
    details_commande = models.ForeignKey(
        DetailsCommande,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='avis'
    )
    note = models.IntegerField(choices=NOTE_CHOICES)
    commentaire = models.TextField(blank=True)
    date_avis = models.DateField(auto_now_add=True)
    verifie_achat = models.BooleanField(
        default=False,
        help_text="True si le client a bien acheté ce produit"
    )

    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        # Un seul avis par client par produit
        unique_together = ('client', 'produit')

    def __str__(self):
        return f"Avis {self.note}/5 sur {self.produit.nom}"