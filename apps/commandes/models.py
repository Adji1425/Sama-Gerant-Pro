from django.db import models
from apps.users.models import Client
from apps.produits.models import Produit, OffreProduit


class Panier(models.Model):
    client = models.OneToOneField(
        Client, on_delete=models.CASCADE, related_name='panier'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Panier"

    def __str__(self):
        return f"Panier de {self.client}"

    def total(self):
        return sum(ligne.sous_total() for ligne in self.lignes.all())

    def vider(self):
        self.lignes.all().delete()


class LignePanier(models.Model):
    panier = models.ForeignKey(
        Panier, on_delete=models.CASCADE, related_name='lignes'
    )
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.IntegerField(default=1)
    prix_unitaire_snapshot = models.FloatField()

    class Meta:
        verbose_name = "Ligne Panier"

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom}"

    def sous_total(self):
        return self.quantite * self.prix_unitaire_snapshot


class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_preparation', 'En préparation'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='commandes'
    )
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='en_attente'
    )
    adresse_livraison_reel = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20)
    montant_total = models.FloatField(default=0)

    class Meta:
        verbose_name = "Commande"
        ordering = ['-date_commande']

    def __str__(self):
        return f"Commande #{self.id} - {self.client}"

    def calculer_montant(self):
        total = sum(d.sous_total() for d in self.details.all())
        self.montant_total = total
        self.save()


class DetailsCommande(models.Model):
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name='details'
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.SET_NULL, null=True
    )
    offre = models.ForeignKey(
        OffreProduit, on_delete=models.SET_NULL, null=True, blank=True
    )
    quantite = models.IntegerField()
    prix_unitaire_vente = models.FloatField()

    class Meta:
        verbose_name = "Détail Commande"

    def __str__(self):
        return f"{self.quantite} x {self.produit}"

    def sous_total(self):
        if self.offre and self.offre.est_active():
            remise = self.prix_unitaire_vente * (self.offre.taux / 100)
            return self.quantite * (self.prix_unitaire_vente - remise)
        return self.quantite * self.prix_unitaire_vente
