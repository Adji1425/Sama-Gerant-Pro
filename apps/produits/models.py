from django.db import models
from apps.users.models import Commercant


class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Catégorie"

    def __str__(self):
        return self.nom


class Produit(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('archive', 'Archivé'),
    ]
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='produits'
    )
    categorie = models.ForeignKey(
        Categorie, on_delete=models.SET_NULL, null=True, related_name='produits'
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prix_achat = models.FloatField()
    prix_vente = models.FloatField()
    frais_packaging = models.FloatField(default=0)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='actif')
    quantite = models.IntegerField(default=0)
    seuil_alerte = models.IntegerField(default=5)
    seuil_dormant = models.IntegerField(default=60)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produit"

    def __str__(self):
        return self.nom

    def marge_nette(self):
        return self.prix_vente - self.prix_achat - self.frais_packaging

    def est_en_alerte(self):
        return self.quantite <= self.seuil_alerte

    def note_moyenne(self):
        avis = self.avis_set.all()
        if avis.exists():
            return round(sum(a.note for a in avis) / avis.count(), 1)
        return 0


class ImageProd(models.Model):
    produit = models.ForeignKey(
        Produit, on_delete=models.CASCADE, related_name='images'
    )
    url = models.ImageField(upload_to='produits/')
    nom = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Image Produit"

    def __str__(self):
        return f"Image de {self.produit.nom}"


class OffreProduit(models.Model):
    produit = models.OneToOneField(
        Produit, on_delete=models.CASCADE, related_name='offre'
    )
    titre = models.CharField(max_length=150)
    taux = models.FloatField(help_text="Taux de réduction en %")
    description = models.TextField(blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField()

    class Meta:
        verbose_name = "Offre Produit"

    def __str__(self):
        return f"{self.titre} - {self.taux}%"

    def est_active(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.date_debut <= today <= self.date_fin


class Depense(models.Model):
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='depenses'
    )
    montant = models.FloatField()
    date = models.DateField()
    type = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Dépense"

    def __str__(self):
        return f"{self.type} - {self.montant} FCFA"
