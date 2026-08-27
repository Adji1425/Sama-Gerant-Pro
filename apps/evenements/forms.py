from django import forms
from .models import EvenementSAD


class EvenementSADForm(forms.ModelForm):
    class Meta:
        model = EvenementSAD
        fields = ['nom_evenement', 'date_debut', 'date_fin', 'conseil_affiche']
        widgets = {
            'nom_evenement': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Tabaski, Magal, Korité...'
            }),
            'date_debut': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'date_fin': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'conseil_affiche': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': "Conseil affiché au commerçant avant l'événement..."
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        debut = cleaned_data.get('date_debut')
        fin = cleaned_data.get('date_fin')
        if debut and fin and fin < debut:
            raise forms.ValidationError(
                "La date de fin doit être postérieure ou égale à la date de début."
            )
        return cleaned_data