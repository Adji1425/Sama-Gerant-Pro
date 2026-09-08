from django.contrib import admin
from .models import ConfigurationClimatique


@admin.register(ConfigurationClimatique)
class ConfigurationClimatiqueAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'icone', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'code')
