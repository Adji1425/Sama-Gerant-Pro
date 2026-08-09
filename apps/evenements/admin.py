from django.contrib import admin
from .models import EvenementSAD


@admin.register(EvenementSAD)
class EvenementSADAdmin(admin.ModelAdmin):
    list_display = ('nom_evenement', 'date_debut', 'date_fin')
    list_filter = ('date_debut',)
    search_fields = ('nom_evenement',)
