from django import forms
from .models import ConfigurationClimatique


class ConfigurationClimatiqueForm(forms.ModelForm):
    class Meta:
        model = ConfigurationClimatique
        fields = ['nom', 'code', 'icone', 'conseil', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Hivernage'
            }),
            'code': forms.Select(attrs={'class': 'form-select'}),
            'icone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : bi-cloud-rain-heavy'
            }),
            'conseil': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Conseil affiché au commerçant durant cette saison...'
            }),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'code': "La saison est détectée automatiquement via l'API météo "
                    "(précipitations + températures réelles à Dakar) ; ce texte "
                    "s'affichera quand elle correspond.",
        }
