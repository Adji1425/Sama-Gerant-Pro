from django import forms
from .models import ConfigurationClimatique


class ConfigurationClimatiqueForm(forms.ModelForm):
    class Meta:
        model = ConfigurationClimatique
        fields = [
            'nom', 'code', 'mois_debut', 'jour_debut',
            'mois_fin', 'jour_fin', 'icone', 'conseil', 'actif',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Hivernage'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : hivernage'
            }),
            'mois_debut': forms.Select(attrs={'class': 'form-select'}),
            'jour_debut': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'max': 31
            }),
            'mois_fin': forms.Select(attrs={'class': 'form-select'}),
            'jour_fin': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'max': 31
            }),
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

    def clean(self):
        cleaned_data = super().clean()
        for prefix in ('debut', 'fin'):
            mois = cleaned_data.get(f'mois_{prefix}')
            jour = cleaned_data.get(f'jour_{prefix}')
            if mois and jour:
                import calendar
                max_jour = calendar.monthrange(2001, mois)[1]  # année non bissextile
                if jour > max_jour:
                    self.add_error(
                        f'jour_{prefix}',
                        f"Ce mois ne comporte que {max_jour} jours."
                    )
        return cleaned_data
