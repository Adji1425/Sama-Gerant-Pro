import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Utilisateur, Client


# Caractères spéciaux acceptés dans le mot de passe
CARACTERES_SPECIAUX = r"""!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?"""


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
        max_length=9,
        min_length=9,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '9 chiffres, ex: 771234567',
            'maxlength': '9'
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
            'placeholder': '8 caractères min. avec 1 caractère spécial'
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

    def clean_username(self):
        """Le nom d'utilisateur doit être unique"""
        username = self.cleaned_data.get('username')
        if Utilisateur.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                "Ce nom d'utilisateur est déjà utilisé. Choisissez-en un autre."
            )
        return username

    def clean_email(self):
        """L'email doit être unique"""
        email = self.cleaned_data.get('email')
        if Utilisateur.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "Un compte existe déjà avec cet email."
            )
        return email

    def clean_telephone(self):
        """Le téléphone doit contenir exactement 9 chiffres"""
        telephone = self.cleaned_data.get('telephone', '').strip()
        if not telephone.isdigit():
            raise ValidationError(
                "Le numéro de téléphone ne doit contenir que des chiffres."
            )
        if len(telephone) != 9:
            raise ValidationError(
                "Le numéro de téléphone doit contenir exactement 9 chiffres."
            )
        return telephone

    def clean_password1(self):
        """Le mot de passe doit faire 8 caractères min. et contenir un caractère spécial"""
        password1 = self.cleaned_data.get('password1', '')

        if len(password1) < 8:
            raise ValidationError(
                "Le mot de passe doit contenir au moins 8 caractères."
            )
        if not re.search(f"[{CARACTERES_SPECIAUX}]", password1):
            raise ValidationError(
                "Le mot de passe doit contenir au moins un caractère spécial "
                "(ex: ! @ # $ % & * - _ .)."
            )

        # Validateurs natifs Django (similarité avec les infos utilisateur, mdp trop commun, etc.)
        validate_password(password1, self.instance)

        return password1


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


class ChangerMotDePasseForm(forms.Form):
    """Formulaire de changement de mot de passe (utilisateur connecté)"""
    ancien_mot_de_passe = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )
    nouveau_mot_de_passe1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '8 caractères min. avec 1 caractère spécial'
        })
    )
    nouveau_mot_de_passe2 = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_ancien_mot_de_passe(self):
        ancien = self.cleaned_data.get('ancien_mot_de_passe')
        if not self.user.check_password(ancien):
            raise ValidationError("Le mot de passe actuel est incorrect.")
        return ancien

    def clean_nouveau_mot_de_passe1(self):
        password1 = self.cleaned_data.get('nouveau_mot_de_passe1', '')

        if len(password1) < 8:
            raise ValidationError(
                "Le nouveau mot de passe doit contenir au moins 8 caractères."
            )
        if not re.search(f"[{CARACTERES_SPECIAUX}]", password1):
            raise ValidationError(
                "Le nouveau mot de passe doit contenir au moins un caractère "
                "spécial (ex: ! @ # $ % & * - _ .)."
            )

        validate_password(password1, self.user)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('nouveau_mot_de_passe1')
        password2 = cleaned_data.get('nouveau_mot_de_passe2')

        if password1 and password2 and password1 != password2:
            self.add_error(
                'nouveau_mot_de_passe2',
                "Les deux mots de passe ne correspondent pas."
            )
        return cleaned_data

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['nouveau_mot_de_passe1'])
        if commit:
            self.user.save()
        return self.user


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

    def clean_email(self):
        """L'email doit rester unique (hors compte courant)"""
        email = self.cleaned_data.get('email')
        qs = Utilisateur.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Un autre compte utilise déjà cet email.")
        return email

    def clean_telephone(self):
        """Le téléphone doit contenir exactement 9 chiffres"""
        telephone = self.cleaned_data.get('telephone', '').strip()
        if telephone:
            if not telephone.isdigit():
                raise ValidationError(
                    "Le numéro de téléphone ne doit contenir que des chiffres."
                )
            if len(telephone) != 9:
                raise ValidationError(
                    "Le numéro de téléphone doit contenir exactement 9 chiffres."
                )
        return telephone