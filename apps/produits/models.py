from django.db import models
from django.utils import timezone
from apps.users.models import Commercant, Client


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
        # Suppression "douce" (§5.2.1 du cahier des charges : "conserver
        # l'historique des données pour ne pas fausser les analyses
        # financières du SAD"). Le produit disparaît de tous les listings
        # (catalogue, actifs, archivés) mais la ligne reste en base, donc
        # les anciennes commandes/factures qui le référencent restent
        # intactes et les statistiques historiques ne sont pas faussées.
        ('supprime', 'Supprimé'),
    ]

    # Chaque variante (couleur/taille) d'un article est enregistrée comme
    # un produit à part entière, avec son propre stock et ses propres
    # images. Ces deux champs sont optionnels : un article sans
    # déclinaison (ex: un jouet) peut les laisser vides.
    TAILLE_CHOICES = [
        ('', 'Sans taille'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='produits'
    )
    categorie = models.ForeignKey(
        Categorie, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='produits'
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prix_achat = models.FloatField()
    prix_vente = models.FloatField()
    frais_packaging = models.FloatField(default=0)
    statut = models.CharField(
        max_length=10, choices=STATUT_CHOICES, default='actif'
    )
    # ✅ Attribut ajouté selon le diagramme
    attribut = models.CharField(
        max_length=255, blank=True,
        help_text="Ex: Matière, marque, particularité..."
    )
    # Couleur et taille de CETTE fiche produit : si un article existe en
    # plusieurs couleurs/tailles, le commerçant crée une fiche par
    # déclinaison (ex: "Sac Lacoste" en marron ET "Sac Lacoste" en bleu),
    # chacune avec son propre stock et ses propres photos. Cela permet au
    # commerçant de savoir exactement quelle déclinaison a été commandée.
    couleur = models.CharField(
        max_length=50, blank=True,
        help_text="Ex: Marron, Bleu, Rose... (laisser vide si non applicable)"
    )
    taille = models.CharField(
        max_length=10, choices=TAILLE_CHOICES, blank=True,
        help_text="Laisser vide si l'article n'a pas de taille (ex: jouet)"
    )
    # Stock intégré
    quantite = models.IntegerField(default=0)
    seuil_alerte = models.IntegerField(default=5)
    seuil_dormant = models.IntegerField(default=60)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-date_creation']

    def __str__(self):
        variante = self.variante_affichee()
        return f"{self.nom} ({variante})" if variante else self.nom

    def marge_nette(self):
        return round(self.prix_vente - self.prix_achat - self.frais_packaging, 2)

    def est_en_alerte(self):
        return self.quantite <= self.seuil_alerte

    def note_moyenne(self):
        avis = self.avis_set.all()
        if avis.exists():
            return round(sum(a.note for a in avis) / avis.count(), 1)
        return 0

    def image_principale(self):
        return self.images.first()

    def variante_affichee(self):
        """Ex: 'Marron' / 'M' / 'Marron · M' / '' si aucun des deux."""
        return " · ".join(filter(None, [self.couleur, self.taille]))


class ImageProd(models.Model):
    produit = models.ForeignKey(
        Produit, on_delete=models.CASCADE, related_name='images'
    )
    image = models.ImageField(upload_to='produits/')
    nom = models.CharField(max_length=100, blank=True)
    est_principale = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Image Produit"
        verbose_name_plural = "Images Produits"

    def __str__(self):
        return f"Image de {self.produit.nom}"


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
        verbose_name_plural = "Dépenses"
        ordering = ['-date']

    def __str__(self):
        return f"{self.type} — {self.montant} FCFA"


class Approvisionnement(models.Model):
    """
    Enregistre chaque achat fournisseur du commerçant.
    Met à jour automatiquement le stock du produit à la création.
    """
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE,
        related_name='approvisionnements'
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.CASCADE,
        related_name='approvisionnements'
    )
    quantite = models.IntegerField(
        help_text="Quantité reçue du fournisseur"
    )
    prix_achat_unitaire = models.FloatField(
        help_text="Prix d'achat unitaire lors de cet approvisionnement"
    )
    fournisseur = models.CharField(
        max_length=200, blank=True,
        help_text="Nom du fournisseur (optionnel)"
    )
    note = models.TextField(
        blank=True,
        help_text="Remarques sur cet approvisionnement"
    )
    date_approvisionnement = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Approvisionnement"
        verbose_name_plural = "Approvisionnements"
        ordering = ['-date_approvisionnement']

    def __str__(self):
        return (
            f"{self.quantite} x {self.produit.nom} "
            f"le {self.date_approvisionnement}"
        )

    def save(self, *args, **kwargs):
        """
        À la création uniquement :
        - Incrémente le stock du produit
        - Met à jour le prix d'achat si différent
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.produit.quantite += self.quantite
            if self.prix_achat_unitaire != self.produit.prix_achat:
                self.produit.prix_achat = self.prix_achat_unitaire
            self.produit.save()

class Favori(models.Model):
    """Un produit mis en favori (liste de souhaits) par un client"""
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='favoris'
    )
    produit = models.ForeignKey(
        'Produit', on_delete=models.CASCADE, related_name='favorise_par'
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        unique_together = ('client', 'produit')
        ordering = ['-date_ajout']

    def __str__(self):
        return f"{self.client.utilisateur.username} ♥ {self.produit.nom}"
