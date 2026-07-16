from django.db import models
from django.utils import timezone
from apps.users.models import Commercant


class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.nom


class Produit(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('archive', 'Archivé'),
    ]
    commercant = models.ForeignKey(
        Commercant,
        on_delete=models.CASCADE,
        related_name='produits'
    )
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produits'
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prix_achat = models.FloatField()
    prix_vente = models.FloatField()
    frais_packaging = models.FloatField(default=0)
    statut = models.CharField(
        max_length=10, choices=STATUT_CHOICES, default='actif'
    )
    # Stock intégré dans Produit
    quantite = models.IntegerField(default=0)
    seuil_alerte = models.IntegerField(
        default=5,
        help_text="Alerte quand le stock descend sous ce seuil"
    )
    seuil_dormant = models.IntegerField(
        default=60,
        help_text="Nb de jours sans vente avant alerte stock dormant"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-date_creation']

    def __str__(self):
        return self.nom

    def marge_nette(self):
        """Calcule la marge nette du produit"""
        return self.prix_vente - self.prix_achat - self.frais_packaging

    def est_en_alerte(self):
        """Retourne True si le stock est sous le seuil"""
        return self.quantite <= self.seuil_alerte

    def note_moyenne(self):
        """Calcule la note moyenne des avis"""
        avis = self.avis_set.all()
        if avis.exists():
            return round(sum(a.note for a in avis) / avis.count(), 1)
        return 0

    def image_principale(self):
        """Retourne la première image du produit"""
        return self.images.first()


class ImageProd(models.Model):
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='produits/')
    nom = models.CharField(max_length=100, blank=True)
    est_principale = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Image Produit"
        verbose_name_plural = "Images Produits"

    def __str__(self):
        return f"Image de {self.produit.nom}"


class OffreProduit(models.Model):
    """Promotion applicable sur un produit"""
    produit = models.OneToOneField(
        Produit,
        on_delete=models.CASCADE,
        related_name='offre'
    )
    titre = models.CharField(max_length=150)
    taux = models.FloatField(help_text="Taux de réduction en %")
    description = models.TextField(blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField()

    class Meta:
        verbose_name = "Offre Produit"
        verbose_name_plural = "Offres Produits"

    def __str__(self):
        return f"{self.titre} — {self.taux}%"

    def est_active(self):
        today = timezone.now().date()
        return self.date_debut <= today <= self.date_fin

    def prix_reduit(self):
        remise = self.produit.prix_vente * (self.taux / 100)
        return round(self.produit.prix_vente - remise, 2)


class Depense(models.Model):
    """Dépenses du commerçant pour le calcul de marge réelle"""
    commercant = models.ForeignKey(
        Commercant,
        on_delete=models.CASCADE,
        related_name='depenses'
    )
    montant = models.FloatField()
    date = models.DateField()
    type = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        ordering = ['-date']

    def __str__(self):
        return f"{self.type} — {self.montant} FCFA"