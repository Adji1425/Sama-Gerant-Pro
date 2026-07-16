from django.db import models
from django.contrib.auth.models import AbstractUser


class Utilisateur(AbstractUser):
    """Classe de base commune à tous les utilisateurs"""
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('commercant', 'Commerçant'),
        ('admin', 'Administrateur'),
    ]
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='client'
    )
    photo_profile = models.ImageField(
        upload_to='profils/', blank=True, null=True
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    def est_client(self):
        return self.role == 'client'

    def est_commercant(self):
        return self.role == 'commercant'

    def est_admin(self):
        return self.role == 'admin'


class Client(models.Model):
    """Profil étendu pour les clients"""
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='client'
    )
    adresse_livraison = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return f"Client : {self.utilisateur.get_full_name()}"


class Commercant(models.Model):
    """Profil étendu pour les commerçants"""
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='commercant'
    )
    nom_boutique = models.CharField(max_length=150)
    logo = models.ImageField(
        upload_to='logos/', blank=True, null=True
    )

    class Meta:
        verbose_name = "Commerçant"
        verbose_name_plural = "Commerçants"

    def __str__(self):
        return self.nom_boutique


class Administrateur(models.Model):
    """Profil étendu pour les administrateurs"""
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='administrateur'
    )

    class Meta:
        verbose_name = "Administrateur"
        verbose_name_plural = "Administrateurs"

    def __str__(self):
        return f"Admin : {self.utilisateur.get_full_name()}"