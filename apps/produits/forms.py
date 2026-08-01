from django import forms
from .models import Produit, OffreProduit, Depense, Approvisionnement


class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'nom', 'categorie', 'description',
            'prix_achat', 'prix_vente', 'frais_packaging',
            'attribut', 'quantite', 'seuil_alerte', 'seuil_dormant'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit'}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prix_achat': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'prix_vente': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'frais_packaging': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'attribut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Taille S/M/L, Couleur...'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control'}),
            'seuil_dormant': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nom': 'Nom du produit',
            'prix_achat': "Prix d'achat (FCFA)",
            'prix_vente': 'Prix de vente (FCFA)',
            'frais_packaging': 'Frais packaging (FCFA)',
            'attribut': 'Attribut (taille, couleur...)',
            'quantite': 'Quantité initiale en stock',
            'seuil_alerte': "Seuil d'alerte stock bas",
            'seuil_dormant': 'Jours sans vente (stock dormant)',
        }


class OffreProduitForm(forms.ModelForm):
    class Meta:
        model = OffreProduit
        fields = ['titre', 'taux', 'description', 'date_debut', 'date_fin']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'taux': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 20'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'taux': 'Taux de réduction (%)',
            'date_debut': 'Date début',
            'date_fin': 'Date fin',
        }


class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['montant', 'date', 'type', 'description']
        widgets = {
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Transport, Emballage...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ApprovisionnementForm(forms.ModelForm):
    class Meta:
        model = Approvisionnement
        fields = ['produit', 'quantite', 'prix_achat_unitaire', 'fournisseur', 'note']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité reçue'}),
            'prix_achat_unitaire': forms.NumberInput(attrs={'class': 'form-control'}),
            'fournisseur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du fournisseur'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'prix_achat_unitaire': "Prix d'achat unitaire (FCFA)",
            'fournisseur': 'Fournisseur (optionnel)',
        }