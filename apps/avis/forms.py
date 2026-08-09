from django import forms
from .models import Avis


class AvisForm(forms.ModelForm):
    class Meta:
        model = Avis
        fields = ['note', 'commentaire']
        widgets = {
            'note': forms.Select(
                choices=[(i, f"{i} étoile(s)") for i in range(1, 6)],
                attrs={'class': 'form-select'},
            ),
            'commentaire': forms.Textarea(attrs={
                'rows': 3, 'class': 'form-control', 'placeholder': "Votre avis sur ce produit...",
            }),
        }
