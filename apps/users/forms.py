from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Utilisateur, Client


class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription pour un client"""
    first_name = forms.CharField(
        max_length=50,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre prénom'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom'
        })
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com'
        })
    )
    telephone = forms.CharField(
        max_length=20,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '77 000 00 00'
        })
    )
    adresse_livraison = forms.CharField(
        max_length=255,
        label="Adresse de livraison",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre adresse habituelle'
        })
    )
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )

    class Meta:
        model = Utilisateur
        fields = [
            'first_name', 'last_name', 'username',
            'email', 'telephone', 'password1', 'password2'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Nom d'utilisateur"
            })
        }


class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion"""
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Nom d'utilisateur"
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )


class ModifierProfilForm(forms.ModelForm):
    """Formulaire de modification du profil"""
    class Meta:
        model = Utilisateur
        fields = ['first_name', 'last_name', 'email',
                  'telephone', 'adresse', 'photo_profile']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'photo_profile': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Email',
            'telephone': 'Téléphone',
            'adresse': 'Adresse',
            'photo_profile': 'Photo de profil',
        }