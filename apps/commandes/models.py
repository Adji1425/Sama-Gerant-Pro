from django.db import models
from apps.users.models import Client
from apps.produits.models import Produit, OffreProduit


class Panier(models.Model):
    client = models.OneToOneField(
        Client, on_delete=models.CASCADE, related_name='panier'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Panier"

    def __str__(self):
        return f"Panier de {self.client}"

    def total(self):
        return sum(
            ligne.sous_total()
            for ligne in self.lignes.all()
        )

    def nombre_articles(self):
        return sum(ligne.quantite for ligne in self.lignes.all())

    def vider(self):
        self.lignes.all().delete()


class LignePanier(models.Model):
    """
    Joue 2 rôles selon le diagramme :
    - Si commande = None  → ligne temporaire du panier
    - Si commande = renseignée → ligne archivée de la commande
    """
    panier = models.ForeignKey(
        Panier,
        on_delete=models.CASCADE,
        related_name='lignes'
    )
    # Lien vers la commande une fois validée
    commande = models.ForeignKey(
        'Commande',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lignes'
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.SET_NULL,
        null=True
    )
    offre = models.ForeignKey(
        OffreProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    quantite = models.IntegerField(default=1)
    # Prix figé au moment de l'ajout au panier
    prix_unitaire_vente = models.FloatField()

    class Meta:
        verbose_name = "Ligne Panier"
        verbose_name_plural = "Lignes Panier"

    def __str__(self):
        return f"{self.quantite} x {self.produit}"

    def sous_total(self):
        if self.offre and self.offre.est_active():
            remise = self.prix_unitaire_vente * (self.offre.taux / 100)
            return round(
                self.quantite * (self.prix_unitaire_vente - remise), 2
            )
        return round(self.quantite * self.prix_unitaire_vente, 2)

    def save(self, *args, **kwargs):
        # Capture automatique du prix au moment de l'ajout
        if not self.prix_unitaire_vente and self.produit:
            self.prix_unitaire_vente = self.produit.prix_vente
        super().save(*args, **kwargs)


class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_preparation', 'En préparation'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='commandes'
    )
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente'
    )
    adresse_livraison_reel = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20)
    montant_total = models.FloatField(default=0)

    class Meta:
        verbose_name = "Commande"
        ordering = ['-date_commande']

    def __str__(self):
        return f"Commande #{self.id} — {self.client}"

    def changer_statut(self, nouveau_statut):
        self.statut = nouveau_statut
        self.save()

    def calculer_montant(self):
        total = sum(l.sous_total() for l in self.lignes.all())
        self.montant_total = total
        self.save()
        return total