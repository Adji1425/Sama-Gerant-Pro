from django import forms
from .models import Produit,Depense, Approvisionnement, Categorie


class ProduitForm(forms.ModelForm):
    categorie = forms.ModelChoiceField(
        queryset=Categorie.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Catégorie',
    )
    nouvelle_categorie = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control mt-2',
            'placeholder': "Ou créer une nouvelle catégorie..."
        }),
        label='',
    )

    class Meta:
        model = Produit
        fields = [
            'nom', 'categorie', 'description',
            'prix_achat', 'prix_vente', 'frais_packaging',
            'attribut', 'quantite', 'seuil_alerte', 'seuil_dormant'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prix_achat': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0', 'step': '1'}),
            'prix_vente': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0', 'step': '1'}),
            'frais_packaging': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0', 'step': '1'}),
            'attribut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Taille S/M/L, Couleur...'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0', 'step': '1'}),
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'}),
            'seuil_dormant': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'}),
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

    # -- Nombres entiers positifs uniquement (pas de virgule, pas de négatif) --
    def _positif_entier(self, nom_champ, label):
        valeur = self.cleaned_data.get(nom_champ)
        if valeur is None:
            return valeur
        if valeur != int(valeur):
            raise forms.ValidationError(f"{label} doit être un nombre entier, sans virgule.")
        if valeur < 0:
            raise forms.ValidationError(f"{label} ne peut pas être négatif.")
        return int(valeur)

    def clean_prix_achat(self):
        return self._positif_entier('prix_achat', "Le prix d'achat")

    def clean_prix_vente(self):
        return self._positif_entier('prix_vente', "Le prix de vente")

    def clean_frais_packaging(self):
        return self._positif_entier('frais_packaging', "Les frais de packaging")

    def clean_quantite(self):
        return self._positif_entier('quantite', "La quantité")

    def clean_seuil_alerte(self):
        return self._positif_entier('seuil_alerte', "Le seuil d'alerte")

    def clean_seuil_dormant(self):
        return self._positif_entier('seuil_dormant', "Le nombre de jours")
    def clean(self):
        cleaned_data = super().clean()
        categorie = cleaned_data.get('categorie')
        nouvelle = (cleaned_data.get('nouvelle_categorie') or '').strip()

        if nouvelle:
            categorie, _ = Categorie.objects.get_or_create(
                nom__iexact=nouvelle,
                defaults={'nom': nouvelle}
            )
            cleaned_data['categorie'] = categorie
        elif not categorie:
            self.add_error('categorie', "Choisissez une catégorie ou créez-en une nouvelle.")

        # Empêche un produit vendu à perte (prix de vente < coût réel du
        # produit) : bug remonté où un produit acheté à 1000 FCFA pouvait
        # être revendu à 500 FCFA sans avertissement, donnant une marge
        # négative affichée telle quelle sur le tableau de bord.
        prix_achat = cleaned_data.get('prix_achat')
        prix_vente = cleaned_data.get('prix_vente')
        frais_packaging = cleaned_data.get('frais_packaging') or 0

        if prix_achat is not None and prix_vente is not None:
            cout_total = prix_achat + frais_packaging
            if prix_vente < cout_total:
                self.add_error(
                    'prix_vente',
                    f"Le prix de vente ({prix_vente} FCFA) est inférieur au coût "
                    f"du produit ({cout_total} FCFA = prix d'achat + packaging). "
                    f"Vous vendriez à perte : augmentez le prix de vente ou "
                    f"réduisez le prix d'achat/les frais de packaging."
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.categorie = self.cleaned_data.get('categorie')
        if commit:
            instance.save()
        return instance


class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['montant', 'date', 'type', 'description']
        widgets = {
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Transport, Emballage...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant is None:
            return montant
        if montant != int(montant):
            raise forms.ValidationError("Le montant doit être un nombre entier, sans virgule.")
        if montant < 0:
            raise forms.ValidationError("Le montant ne peut pas être négatif.")
        return int(montant)


class ApprovisionnementForm(forms.ModelForm):
    class Meta:
        model = Approvisionnement
        fields = ['produit', 'quantite', 'prix_achat_unitaire', 'fournisseur', 'note']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité reçue', 'min': '1', 'step': '1'}),
            'prix_achat_unitaire': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'}),
            'fournisseur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du fournisseur'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'prix_achat_unitaire': "Prix d'achat unitaire (FCFA)",
            'fournisseur': 'Fournisseur (optionnel)',
        }

    def clean_quantite(self):
        quantite = self.cleaned_data.get('quantite')
        if quantite is None:
            return quantite
        if quantite != int(quantite):
            raise forms.ValidationError("La quantité doit être un nombre entier, sans virgule.")
        if quantite <= 0:
            raise forms.ValidationError("La quantité doit être supérieure à 0.")
        return int(quantite)

    def clean_prix_achat_unitaire(self):
        prix = self.cleaned_data.get('prix_achat_unitaire')
        if prix is None:
            return prix
        if prix != int(prix):
            raise forms.ValidationError("Le prix doit être un nombre entier, sans virgule.")
        if prix < 0:
            raise forms.ValidationError("Le prix ne peut pas être négatif.")
        return int(prix)