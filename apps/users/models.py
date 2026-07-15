from django.db import models
from django.contrib.auth.models import AbstractUser


class Utilisateur(AbstractUser):
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('commercant', 'Commerçant'),
        ('admin', 'Administrateur'),
    ]
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    photo_profile = models.ImageField(upload_to='profils/', blank=True, null=True)

    class Meta:
        verbose_name = "Utilisateur"

    def __str__(self):
        return f"{self.username} ({self.role})"


class Client(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, on_delete=models.CASCADE, related_name='client'
    )
    adresse_livraison = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Client"

    def __str__(self):
        return f"Client : {self.utilisateur.get_full_name()}"


class Commercant(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, on_delete=models.CASCADE, related_name='commercant'
    )
    nom_boutique = models.CharField(max_length=150)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)

    class Meta:
        verbose_name = "Commerçant"

    def __str__(self):
        return self.nom_boutique


class Administrateur(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, on_delete=models.CASCADE, related_name='administrateur'
    )

    class Meta:
        verbose_name = "Administrateur"

    def __str__(self):
        return f"Admin : {self.utilisateur.get_full_name()}"
